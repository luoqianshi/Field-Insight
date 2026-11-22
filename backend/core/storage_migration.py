"""数据根迁移引擎：预检 → 复制 → 校验 → 引用重写 → 切换 → 清理。

计划书：docs/sdd/plans/2026-11-20-settings-storage-migration.md §4
安全契约：
- switching 之前源数据始终完整；失败/取消/中断 = 安全态（目标半成品可续传或清除）
- 全量 SHA-256 校验通过后才原子切换锚点；切换后任何失败不回滚锚点
- 单文件失败错误隔离；清理跳过被占用文件并报告残留（可重试）
- journal 仅为提示，恢复以磁盘实况为准（幂等续传：size+hash 匹配则跳过）
- 外部文件夹（数据根外）不移动不改写；相对路径引用天然兼容
"""
import hashlib
import json
import os
import shutil
import threading
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

import yaml

import config
from core import storage_settings

CHUNK_SIZE = 1024 * 1024
SPACE_FACTOR = 1.1
SPACE_MARGIN_BYTES = 100 * 1024 * 1024
JOURNAL_NAME = ".tjzk_migration.json"


class MigrationError(Exception):
    """迁移业务错误（API 400）。"""


class MigrationBusyError(MigrationError):
    """迁移进行中 / 处理任务运行中（API 409）。"""


class MigrationPrecheckError(MigrationError):
    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


class _Cancelled(Exception):
    pass


def _norm(p) -> str:
    return os.path.normcase(os.path.abspath(str(p)))


def _fmt_bytes(n) -> str:
    n = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024
    return f"{n:.1f} TB"


def _sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _scan_files(root: Path):
    """扫描受管目录 → [(relpath_posix, size)]，按大小升序（小文件先复制，journal 早期可用）。"""
    items = []
    root = Path(root)
    for d in storage_settings.managed_dirs(root):
        if not d.is_dir():
            continue
        for dirpath, _dirs, files in os.walk(str(d)):
            for name in files:
                full = Path(dirpath) / name
                try:
                    size = full.stat().st_size
                except OSError:
                    size = 0
                items.append((full.relative_to(root).as_posix(), size))
    items.sort(key=lambda x: x[1])
    return items


def _is_system_dir(p: Path) -> bool:
    s = _norm(p)
    drive = os.environ.get("SystemDrive", "C:")
    protected = [
        os.environ.get("SystemRoot", r"C:\Windows"),
        drive + "\\Program Files",
        drive + "\\Program Files (x86)",
    ]
    for base in protected:
        b = _norm(base)
        if s == b or s.startswith(b + os.sep):
            return True
    return False


def precheck(target, source=None, skip_space=False) -> dict:
    """目标预检：嵌套/系统目录/可写性/空间/运行中任务。返回报告（ok/errors/warnings/统计）。"""
    source = Path(source) if source is not None else Path(config.PROJECT_ROOT)
    errors, warnings = [], []
    if not target or not str(target).strip():
        return {"ok": False, "errors": ["请指定目标目录"], "warnings": [],
                "source_root": str(source), "target": "",
                "source_size_bytes": 0, "source_file_count": 0, "target_free_bytes": 0}
    tgt = Path(os.path.abspath(str(target).strip()))
    src_n, tgt_n = _norm(source), _norm(tgt)
    if tgt_n == src_n:
        errors.append("目标目录与当前数据位置相同")
    elif tgt_n.startswith(src_n + os.sep):
        errors.append("目标不能位于当前数据目录内部")
    elif src_n.startswith(tgt_n + os.sep):
        errors.append("当前数据目录位于目标内部，无法迁移")
    if _is_system_dir(tgt):
        errors.append("目标不能是系统目录")
    drive_anchor = tgt.anchor
    if drive_anchor and not Path(drive_anchor).exists():
        errors.append(f"目标盘符不存在：{drive_anchor}")

    files = _scan_files(source)
    total_bytes = sum(s for _, s in files)
    free = 0
    if not errors:
        try:
            tgt.mkdir(parents=True, exist_ok=True)
            probe = tgt / f".tjzk_probe_{uuid.uuid4().hex[:8]}"
            probe.write_bytes(b"ok")
            probe.unlink()
        except OSError as exc:
            errors.append(f"目标目录不可写：{exc}")
        try:
            free = shutil.disk_usage(str(tgt)).free
        except OSError:
            free = 0
        need = int(total_bytes * SPACE_FACTOR) + SPACE_MARGIN_BYTES
        if not skip_space and free < need:
            errors.append(f"目标磁盘空间不足：需约 {_fmt_bytes(need)}，仅剩 {_fmt_bytes(free)}")
    if tgt.is_dir():
        try:
            if any(tgt.iterdir()):
                warnings.append("目标目录非空，迁移将写入其受管子目录（其余内容不受影响）")
        except OSError:
            pass
    if drive_anchor and source.anchor and _norm(drive_anchor) != _norm(source.anchor):
        warnings.append("跨盘迁移：复制速度取决于磁盘性能")
    try:
        from core.engine import get_processing_task_manager
        tm = get_processing_task_manager()
        if tm is not None:
            busy = [t for t in tm.list() if t.get("status") in ("pending", "processing")]
            if busy:
                errors.append(f"有 {len(busy)} 个处理任务进行中，请等待完成后再迁移")
    except Exception:
        pass
    return {"ok": not errors, "errors": errors, "warnings": warnings,
            "source_root": str(source), "target": str(tgt),
            "source_size_bytes": total_bytes, "source_file_count": len(files),
            "target_free_bytes": free}


def _rewrite_str(s, old_root, new_root, changed):
    """仅重写以旧根为前缀的绝对路径；相对路径与根外路径不动。"""
    if not isinstance(s, str) or not s:
        return s
    old_base = str(old_root).rstrip("\\/")
    new_base = str(new_root).rstrip("\\/")
    s_n = os.path.normcase(s)
    if s_n == os.path.normcase(old_base):
        changed[0] = True
        return new_base
    for sep in ("\\", "/"):
        prefix = old_base + sep
        if s_n.startswith(os.path.normcase(prefix)):
            changed[0] = True
            return new_base + sep + s[len(prefix):]
    return s


def _rewrite_obj(obj, old_root, new_root, changed):
    if isinstance(obj, dict):
        return {k: _rewrite_obj(v, old_root, new_root, changed) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_rewrite_obj(v, old_root, new_root, changed) for v in obj]
    if isinstance(obj, str):
        return _rewrite_str(obj, old_root, new_root, changed)
    return obj


class StorageMigration:
    """单次迁移任务状态机（镜像 task_manager 的提交/轮询模式）。"""

    def __init__(self):
        self._lock = threading.RLock()
        self._thread = None
        self._cancel = threading.Event()
        self._state = {"phase": "idle", "status": "idle"}
        self._hashes = {}
        self._files = []
        self._speed_samples = deque(maxlen=20)

    # ── 对外接口 ──────────────────────────────────────────────
    def status(self) -> dict:
        with self._lock:
            s = dict(self._state)
            for k in ("errors", "warnings", "residual_files", "verify_mismatches"):
                s[k] = list(s.get(k, []))
        started = s.get("started_at")
        if started:
            end = s.get("completed_at") or time.time()
            s["elapsed_s"] = round(end - started, 1)
        return s

    def is_running(self) -> bool:
        with self._lock:
            return self._state.get("status") == "running"

    def start(self, target, resume=False) -> str:
        with self._lock:
            if self.is_running():
                raise MigrationBusyError("迁移进行中，请等待完成")
            report = precheck(target, skip_space=resume)
            if not report["ok"]:
                raise MigrationPrecheckError(report["errors"])
            mid = f"mig_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"
            self._cancel.clear()
            self._hashes = {}
            self._files = _scan_files(Path(report["source_root"]))
            self._speed_samples.clear()
            self._state = {
                "migration_id": mid, "source_root": report["source_root"],
                "target_root": report["target"], "phase": "copying", "status": "running",
                "progress": 0.0, "copied_files": 0, "total_files": len(self._files),
                "copied_bytes": 0, "total_bytes": report["source_size_bytes"],
                "speed_bps": 0, "current_file": "", "error": None,
                "errors": [], "warnings": report["warnings"], "residual_files": [],
                "verify_mismatches": [], "started_at": time.time(), "completed_at": None,
                "switched": False, "resume": resume,
            }
            storage_settings.write_pending({
                "migration_id": mid, "source_root": report["source_root"],
                "target_root": report["target"], "phase": "copying",
                "started_at": datetime.now(timezone.utc).isoformat(),
            })
            self._thread = threading.Thread(target=self._run, name=f"migration-{mid}", daemon=True)
            self._thread.start()
            return mid

    def cancel(self) -> bool:
        with self._lock:
            if self._state.get("status") != "running":
                return False
            self._cancel.set()
            return True

    def resume(self):
        """中断恢复：switching 前 → 幂等续传；switching 后 → 仅补清理。"""
        info = storage_settings.read_pending()
        if not info:
            raise MigrationError("没有可恢复的中断迁移")
        phase = info.get("phase", "")
        if phase in ("switching", "cleaning"):
            return self._resume_cleanup(info)
        if phase == "completed":
            storage_settings.clear_pending()
            return info.get("migration_id")
        return self.start(info["target_root"], resume=True)

    def rollback(self) -> dict:
        """放弃迁移并清理目标半成品（仅 switching 前允许；源数据完好）。"""
        with self._lock:
            if self.is_running():
                raise MigrationBusyError("迁移进行中，无法放弃")
            st = dict(self._state)
        info = storage_settings.read_pending()
        target = st.get("target_root") or info.get("target_root")
        if not target:
            raise MigrationError("没有可放弃的迁移")
        if st.get("switched") or info.get("phase") in ("switching", "cleaning", "completed"):
            raise MigrationError("配置已切换，不能放弃；请使用重试清理")
        residual = self._cleanup_dirs(Path(target))
        try:
            (Path(target) / JOURNAL_NAME).unlink()
        except OSError:
            pass
        storage_settings.clear_pending()
        with self._lock:
            self._state = {"phase": "idle", "status": "rolled_back", "residual_files": residual}
        return {"residual_files": residual}

    def cleanup_old(self) -> dict:
        """重试清理旧根残留（切换后，被占用文件释放后调用）。"""
        with self._lock:
            if self.is_running():
                raise MigrationBusyError("迁移进行中")
            st = dict(self._state)
        source = st.get("source_root") if st.get("switched") else None
        if not source:
            info = storage_settings.read_pending()
            if info.get("phase") in ("switching", "cleaning"):
                source = info.get("source_root")
        if not source:
            raise MigrationError("没有需要清理的旧位置")
        residual = self._cleanup_dirs(Path(source))
        with self._lock:
            self._state["residual_files"] = residual
        if not residual:
            storage_settings.clear_pending()
            tgt = st.get("target_root")
            if tgt:
                try:
                    (Path(tgt) / JOURNAL_NAME).unlink()
                except OSError:
                    pass
        return {"residual_files": residual}

    def wait(self, timeout=None):
        t = self._thread
        if t is not None:
            t.join(timeout)

    # ── 内部流水线 ────────────────────────────────────────────
    def _run(self):
        src = Path(self._state["source_root"])
        tgt = Path(self._state["target_root"])
        try:
            self._copy_phase(src, tgt)
            self._check_cancel()
            self._verify_phase(src, tgt)
            self._rewrite_phase(src, tgt)
            self._switch_phase(tgt)
            self._cleanup_phase(src)
            with self._lock:
                residual = self._state["residual_files"]
            self._finish("completed_with_warnings" if residual else "completed")
        except _Cancelled:
            self._finish("cancelled")
        except Exception as exc:
            with self._lock:
                switched = self._state.get("switched", False)
            if switched:
                self._finish("completed_with_warnings", error=str(exc))
            else:
                self._finish("failed", error=str(exc))

    def _run_cleanup_only(self):
        src = Path(self._state["source_root"])
        try:
            self._cleanup_phase(src)
            with self._lock:
                residual = self._state["residual_files"]
            self._finish("completed_with_warnings" if residual else "completed")
        except Exception as exc:
            self._finish("completed_with_warnings", error=str(exc))

    def _check_cancel(self):
        if self._cancel.is_set():
            raise _Cancelled()

    def _set_phase(self, phase):
        with self._lock:
            self._state["phase"] = phase
        info = storage_settings.read_pending()
        if info:
            info["phase"] = phase
            storage_settings.write_pending(info)

    def _advance(self, rel, size):
        now = time.time()
        with self._lock:
            st = self._state
            st["copied_files"] += 1
            st["copied_bytes"] += size
            st["current_file"] = rel
            self._speed_samples.append((now, st["copied_bytes"]))
            if len(self._speed_samples) >= 2:
                t0, b0 = self._speed_samples[0]
                dt = now - t0
                st["speed_bps"] = int((st["copied_bytes"] - b0) / dt) if dt > 0 else 0
            total = st["total_bytes"] or 1
            st["progress"] = round(min(st["copied_bytes"] / total, 1.0) * 80, 1)

    def _copy_phase(self, src, tgt):
        self._set_phase("copying")
        last_journal = 0.0
        n = 0
        for rel, size in self._files:
            self._check_cancel()
            s = src / rel
            d = tgt / rel
            try:
                d.parent.mkdir(parents=True, exist_ok=True)
                if d.exists() and d.stat().st_size == size:
                    # 幂等续传：size 一致且双端哈希一致 → 跳过
                    sh = _sha256_file(s)
                    if _sha256_file(d) == sh:
                        self._hashes[rel] = sh
                        self._advance(rel, size)
                        continue
                h = hashlib.sha256()
                with open(s, "rb") as fi, open(d, "wb") as fo:
                    while True:
                        chunk = fi.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        h.update(chunk)
                        fo.write(chunk)
                shutil.copystat(str(s), str(d))
                self._hashes[rel] = h.hexdigest()
                self._advance(rel, size)
            except _Cancelled:
                raise
            except Exception as exc:
                with self._lock:
                    self._state["errors"].append({"path": rel, "error": str(exc)})
            n += 1
            now = time.time()
            if n % 50 == 0 or now - last_journal >= 2.0:
                self._write_journal(tgt)
                last_journal = now
        self._write_journal(tgt)
        with self._lock:
            errs = self._state["errors"]
        if errs:
            raise MigrationError(f"{len(errs)} 个文件复制失败（被占用或权限不足），源数据完好")

    def _verify_phase(self, src, tgt):
        """独立全量复核：清单一致性 + size + SHA-256（不信任复制期记录）。"""
        self._set_phase("verifying")
        src_files = dict(_scan_files(src))
        tgt_files = dict(_scan_files(tgt))
        mismatches = []
        for rel in sorted(set(src_files) - set(tgt_files)):
            mismatches.append({"path": rel, "reason": "目标缺失文件"})
        for rel in sorted(set(tgt_files) - set(src_files)):
            mismatches.append({"path": rel, "reason": "目标多出文件"})
        common = sorted(set(src_files) & set(tgt_files))
        done = 0
        for rel in common:
            self._check_cancel()
            s, d = src / rel, tgt / rel
            try:
                if src_files[rel] != tgt_files[rel]:
                    mismatches.append({"path": rel, "reason": "文件大小不一致"})
                else:
                    expected = self._hashes.get(rel)
                    actual = _sha256_file(d)
                    if expected is None:
                        expected = _sha256_file(s)
                    if actual != expected:
                        mismatches.append({"path": rel, "reason": "SHA-256 不一致"})
            except Exception as exc:
                mismatches.append({"path": rel, "reason": f"读取失败: {exc}"})
            done += 1
            with self._lock:
                self._state["progress"] = round(80 + (done / max(len(common), 1)) * 15, 1)
        with self._lock:
            self._state["verify_mismatches"] = mismatches
        if mismatches:
            raise MigrationError(f"完整性校验未通过（{len(mismatches)} 个文件不一致），旧数据未受影响")

    def _rewrite_phase(self, src, tgt):
        """只改目标副本：旧根内部绝对路径 → 新根；相对/根外路径不动。"""
        self._set_phase("rewriting")
        old_root, new_root = str(src), str(tgt)
        for rel in ("data/batches.yaml", "data/processing_tasks.yaml", "datasets/datasets.yaml"):
            p = tgt / rel
            if not p.is_file():
                continue
            data = yaml.safe_load(p.read_text(encoding="utf-8"))
            changed = [False]
            new_data = _rewrite_obj(data, old_root, new_root, changed)
            if changed[0]:
                text = yaml.safe_dump(new_data, allow_unicode=True, sort_keys=False,
                                      default_flow_style=False)
                yaml.safe_load(text)  # 写前校验
                p.write_text(text, encoding="utf-8")
        results_dir = tgt / "results"
        if results_dir.is_dir():
            for sub in sorted(results_dir.iterdir()):
                if not sub.is_dir():
                    continue
                for name in ("meta.json", "counting_data.json"):
                    p = sub / name
                    if not p.is_file():
                        continue
                    data = json.loads(p.read_text(encoding="utf-8"))
                    changed = [False]
                    new_data = _rewrite_obj(data, old_root, new_root, changed)
                    if changed[0]:
                        text = json.dumps(new_data, ensure_ascii=False, indent=2, default=str)
                        json.loads(text)  # 写前校验
                        p.write_text(text, encoding="utf-8")
        with self._lock:
            self._state["progress"] = 97.0

    def _switch_phase(self, tgt):
        self._set_phase("switching")
        storage_settings.write_anchor(str(tgt))
        with self._lock:
            self._state["switched"] = True
            self._state["progress"] = 98.0
        info = storage_settings.read_pending()
        if info:
            info["phase"] = "switching"
            storage_settings.write_pending(info)

    def _cleanup_phase(self, src):
        self._set_phase("cleaning")
        residual = self._cleanup_dirs(src)
        with self._lock:
            self._state["residual_files"] = residual
            self._state["progress"] = 100.0

    def _cleanup_dirs(self, root):
        """删除受管目录（绝不删除根本身）；逐文件错误隔离，残留报告。"""
        residual = []
        for d in storage_settings.managed_dirs(root):
            if not d.exists():
                continue
            for dirpath, dirnames, filenames in os.walk(str(d), topdown=False):
                for name in filenames:
                    full = os.path.join(dirpath, name)
                    try:
                        os.unlink(full)
                    except OSError as exc:
                        residual.append({"path": full, "error": str(exc)})
                for name in dirnames:
                    try:
                        os.rmdir(os.path.join(dirpath, name))
                    except OSError:
                        pass  # 非空（含残留）或被占用，保留
            try:
                d.rmdir()
            except OSError:
                pass
        return residual

    def _resume_cleanup(self, info):
        with self._lock:
            if self.is_running():
                raise MigrationBusyError("迁移进行中")
            mid = info.get("migration_id") or f"mig_{uuid.uuid4().hex[:8]}"
            self._cancel.clear()
            self._state = {
                "migration_id": mid, "source_root": info["source_root"],
                "target_root": info["target_root"], "phase": "cleaning", "status": "running",
                "progress": 98.0, "copied_files": 0, "total_files": 0, "copied_bytes": 0,
                "total_bytes": 0, "speed_bps": 0, "current_file": "", "error": None,
                "errors": [], "warnings": [], "residual_files": [], "verify_mismatches": [],
                "started_at": time.time(), "completed_at": None, "switched": True,
            }
            self._thread = threading.Thread(target=self._run_cleanup_only,
                                            name=f"migration-cleanup-{mid}", daemon=True)
            self._thread.start()
            return mid

    def _write_journal(self, tgt):
        with self._lock:
            st = self._state
            data = {
                "migration_id": st["migration_id"], "source_root": st["source_root"],
                "target_root": st["target_root"], "phase": st["phase"],
                "copied_files": st["copied_files"], "total_files": st["total_files"],
                "copied_bytes": st["copied_bytes"], "total_bytes": st["total_bytes"],
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        try:
            p = Path(tgt) / JOURNAL_NAME
            tmp = p.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            os.replace(str(tmp), str(p))
        except OSError:
            pass

    def _finish(self, status, error=None):
        with self._lock:
            self._state["status"] = status
            if status in ("completed", "completed_with_warnings"):
                self._state["phase"] = "completed"
                self._state["progress"] = 100.0
            self._state["completed_at"] = time.time()
            if error:
                self._state["error"] = error
            tgt = self._state.get("target_root")
            phase = self._state.get("phase")
        if status in ("completed", "completed_with_warnings"):
            storage_settings.clear_pending()
            if tgt:
                try:
                    (Path(tgt) / JOURNAL_NAME).unlink()
                except OSError:
                    pass
        else:
            info = storage_settings.read_pending()
            if info:
                info["phase"] = phase
                info["status"] = status
                storage_settings.write_pending(info)


_migration = None
_singleton_lock = threading.Lock()


def get_migration() -> StorageMigration:
    global _migration
    with _singleton_lock:
        if _migration is None:
            _migration = StorageMigration()
        return _migration