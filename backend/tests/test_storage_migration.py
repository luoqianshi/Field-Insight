"""迁移引擎测试：正常/校验失败/取消/续传/残留/预检/重写/中文路径/空根。

计划书测试矩阵自动化子集：T01/T02/T05/T06/T07/T08/T09/T10/T11/T13/T14/T16/T17/T18/T19/T21/T22/T26。
运行：cd backend && python -m pytest tests/test_storage_migration.py -v
"""
import hashlib
import json
import os
import shutil
from types import SimpleNamespace

import pytest
import yaml

import config
from core import storage_migration, storage_settings
from core.storage_migration import (JOURNAL_NAME, MigrationBusyError,
                                    MigrationError, MigrationPrecheckError,
                                    StorageMigration, precheck)

WEB_DIRS = ("data", "output", "datasets", "results", "models")

# 迁移会按设计重写根内绝对路径的注册表文件（语义正确性由 test_path_rewriting 验证），
# 字节级哈希审计排除这些文件，其余文件必须零差异。
REWRITABLE = {
    "data/batches.yaml", "data/processing_tasks.yaml", "datasets/datasets.yaml",
    "results/count_001/meta.json", "results/count_001/counting_data.json",
}


def _audit(root, include_rewritable=True):
    """独立哈希审计：受管目录全部文件的 {relpath: sha256}。"""
    out = {}
    for name in WEB_DIRS:
        d = root / name
        if not d.is_dir():
            continue
        for p in sorted(d.rglob("*")):
            if p.is_file():
                rel = p.relative_to(root).as_posix()
                if not include_rewritable and rel in REWRITABLE:
                    continue
                out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def _wait(engine, timeout=60):
    engine.wait(timeout)
    st = engine.status()
    assert st["status"] != "running", "迁移超时未结束"
    return st


@pytest.fixture
def mini(tmp_path, monkeypatch):
    """迷你数据根：注册表（相对/根内绝对/根外绝对路径）+ 各模块业务文件。"""
    source = tmp_path / "source"
    default = tmp_path / "default"
    target = tmp_path / "target"
    external = tmp_path / "external_photos"
    for d in WEB_DIRS:
        (source / d).mkdir(parents=True)
    default.mkdir()
    external.mkdir()

    (source / "data" / "images").mkdir()
    (source / "data" / "images" / "a.jpg").write_bytes(b"\xff\xd8fake-jpeg-content-001")
    (source / "data" / "images" / "中文 图片.png").write_bytes(b"png-content-002")
    (source / "output" / "task1").mkdir()
    (source / "output" / "task1" / "x.png").write_bytes(b"processed-003")
    (source / "datasets" / "ds1").mkdir()
    (source / "datasets" / "ds1" / "labels.txt").write_text("0 0.5 0.5 0.2 0.2\n", encoding="utf-8")
    (source / "results" / "count_001").mkdir()
    (source / "models" / "w.pt").write_bytes(b"weights-004")
    (external / "ext.jpg").write_bytes(b"external-005")

    batches = {"batches": [
        {"batch_id": "b1", "batch_name": "架次一", "image_folder_path": "data/images"},
        {"batch_id": "b2", "batch_name": "架次二", "image_folder_path": str(source / "data" / "images")},
        {"batch_id": "b3", "batch_name": "外部架次", "image_folder_path": str(external)},
    ]}
    (source / "data" / "batches.yaml").write_text(
        yaml.safe_dump(batches, allow_unicode=True, sort_keys=False), encoding="utf-8")
    tasks = {"tasks": [{"task_id": "task1", "output_dir": str(source / "output" / "task1"),
                        "input_paths": ["data/images"]}]}
    (source / "data" / "processing_tasks.yaml").write_text(
        yaml.safe_dump(tasks, allow_unicode=True, sort_keys=False), encoding="utf-8")
    datasets = {"datasets": [{"dataset_id": "ds1", "path": str(source / "datasets" / "ds1")}]}
    (source / "datasets" / "datasets.yaml").write_text(
        yaml.safe_dump(datasets, allow_unicode=True, sort_keys=False), encoding="utf-8")
    (source / "results" / "count_001" / "meta.json").write_text(
        json.dumps({"result_id": "count_001", "image_path": str(source / "data" / "images" / "a.jpg")},
                   ensure_ascii=False), encoding="utf-8")
    (source / "results" / "count_001" / "counting_data.json").write_text(
        json.dumps({"source": str(source / "data" / "images")}, ensure_ascii=False), encoding="utf-8")

    monkeypatch.setattr(config, "PROJECT_ROOT", source)
    monkeypatch.setattr(config, "ACTIVE_ROOT", source)
    monkeypatch.setattr(config, "DEFAULT_ROOT", default)
    monkeypatch.setattr(config, "FROZEN", False)
    monkeypatch.setattr(config, "ROOT_FALLBACK_WARNING", None)
    return SimpleNamespace(source=source, default=default, target=target,
                           external=external, tmp=tmp_path)


# ── T01/T02 正常迁移 + 哈希审计 ──────────────────────────────
def test_normal_migration(mini):
    before = _audit(mini.source)
    before_core = _audit(mini.source, include_rewritable=False)
    engine = StorageMigration()
    engine.start(str(mini.target))
    st = _wait(engine)
    assert st["status"] == "completed", st.get("error")
    assert st["progress"] == 100.0
    assert _audit(mini.target, include_rewritable=False) == before_core
    for name in WEB_DIRS:
        assert not (mini.source / name).exists(), f"旧目录未清理: {name}"
    assert storage_settings.configured_root() == str(mini.target)
    assert storage_settings.read_pending() == {}
    assert not (mini.target / JOURNAL_NAME).exists()
    # T19 外部文件夹不移动不改写
    assert (mini.external / "ext.jpg").read_bytes() == b"external-005"


# ── T17/T18 路径引用重写 ─────────────────────────────────────
def test_path_rewriting(mini):
    engine = StorageMigration()
    engine.start(str(mini.target))
    assert _wait(engine)["status"] == "completed"
    batches = yaml.safe_load((mini.target / "data" / "batches.yaml").read_text(encoding="utf-8"))["batches"]
    by_id = {b["batch_id"]: b["image_folder_path"] for b in batches}
    assert by_id["b1"] == "data/images"  # 相对路径不动
    assert os.path.normcase(by_id["b2"]) == os.path.normcase(str(mini.target / "data" / "images"))
    assert by_id["b3"] == str(mini.external)  # 根外绝对路径不动
    tasks = yaml.safe_load((mini.target / "data" / "processing_tasks.yaml").read_text(encoding="utf-8"))["tasks"]
    assert os.path.normcase(tasks[0]["output_dir"]) == os.path.normcase(str(mini.target / "output" / "task1"))
    assert tasks[0]["input_paths"] == ["data/images"]
    ds = yaml.safe_load((mini.target / "datasets" / "datasets.yaml").read_text(encoding="utf-8"))["datasets"]
    assert os.path.normcase(ds[0]["path"]) == os.path.normcase(str(mini.target / "datasets" / "ds1"))
    meta = json.loads((mini.target / "results" / "count_001" / "meta.json").read_text(encoding="utf-8"))
    assert os.path.normcase(meta["image_path"]) == os.path.normcase(str(mini.target / "data" / "images" / "a.jpg"))


# ── T10 校验失败注入：不切换、源完好、可重试 ─────────────────
def test_verify_failure_then_retry(mini, monkeypatch):
    before = _audit(mini.source)
    before_core = _audit(mini.source, include_rewritable=False)
    engine = StorageMigration()
    orig_verify = engine._verify_phase

    def tamper(src, tgt):
        (tgt / "data" / "images" / "a.jpg").write_bytes(b"corrupted")
        return orig_verify(src, tgt)

    monkeypatch.setattr(engine, "_verify_phase", tamper)
    engine.start(str(mini.target))
    st = _wait(engine)
    assert st["status"] == "failed"
    assert st["verify_mismatches"]
    assert storage_settings.configured_root() is None  # 绝不切换
    assert _audit(mini.source) == before  # 源完好
    # 重试（幂等续传修复被篡改文件）
    engine2 = StorageMigration()
    engine2.start(str(mini.target))
    st2 = _wait(engine2)
    assert st2["status"] == "completed", st2.get("error")
    assert _audit(mini.target, include_rewritable=False) == before_core


# ── T09 取消 + T06 续传 ──────────────────────────────────────
def test_cancel_then_resume(mini, monkeypatch):
    before = _audit(mini.source)
    before_core = _audit(mini.source, include_rewritable=False)
    engine = StorageMigration()
    orig_advance = engine._advance

    def advance_then_cancel(rel, size):
        orig_advance(rel, size)
        engine._cancel.set()

    monkeypatch.setattr(engine, "_advance", advance_then_cancel)
    engine.start(str(mini.target))
    st = _wait(engine)
    assert st["status"] == "cancelled"
    assert _audit(mini.source) == before
    assert storage_settings.configured_root() is None
    # 恢复（新引擎模拟重启后恢复卡片）
    engine2 = StorageMigration()
    engine2.resume()
    st2 = _wait(engine2)
    assert st2["status"] == "completed", st2.get("error")
    assert _audit(mini.target, include_rewritable=False) == before_core


# ── 复制期单文件失败：错误隔离 + 整体 failed + 源完好 ────────
def test_copy_error_isolation(mini, monkeypatch):
    before = _audit(mini.source)
    orig_copystat = shutil.copystat

    def selective(s, d):
        if str(d).endswith("w.pt"):
            raise PermissionError("模拟文件占用")
        return orig_copystat(s, d)

    monkeypatch.setattr(storage_migration.shutil, "copystat", selective)
    engine = StorageMigration()
    engine.start(str(mini.target))
    st = _wait(engine)
    assert st["status"] == "failed"
    assert any(e["path"].endswith("w.pt") for e in st["errors"])
    assert _audit(mini.source) == before
    assert storage_settings.configured_root() is None


# ── T08 切换后清理中断：恢复仅补清理 ─────────────────────────
def test_resume_cleanup_after_switch(mini):
    # 手工构造 cleaning 阶段中断现场：目标数据完整 + 锚点已切换 + pending 留存
    for name in WEB_DIRS:
        shutil.copytree(str(mini.source / name), str(mini.target / name))
    storage_settings.write_anchor(str(mini.target))
    storage_settings.write_pending({"migration_id": "m_switched", "phase": "cleaning",
                                    "source_root": str(mini.source), "target_root": str(mini.target)})
    engine = StorageMigration()
    engine.resume()
    st = _wait(engine)
    assert st["status"] == "completed", st.get("error")
    for name in WEB_DIRS:
        assert not (mini.source / name).exists()
    assert storage_settings.read_pending() == {}
    assert storage_settings.configured_root() == str(mini.target)


# ── T09 放弃并清理（rollback）────────────────────────────────
def test_rollback(mini, monkeypatch):
    before = _audit(mini.source)
    engine = StorageMigration()

    def boom(src, tgt):
        raise MigrationError("模拟校验期中断")

    monkeypatch.setattr(engine, "_verify_phase", boom)
    engine.start(str(mini.target))
    assert _wait(engine)["status"] == "failed"
    result = engine.rollback()
    assert result["residual_files"] == []
    for name in WEB_DIRS:
        assert not (mini.target / name).exists()
    assert storage_settings.read_pending() == {}
    assert _audit(mini.source) == before
    assert storage_settings.configured_root() is None


# ── T13/T14 预检拒绝非法目标 ─────────────────────────────────
def test_precheck_rejects_invalid(mini):
    engine = StorageMigration()
    with pytest.raises(MigrationPrecheckError):
        engine.start(str(mini.source))  # 同路径
    with pytest.raises(MigrationPrecheckError):
        engine.start(str(mini.source / "data" / "sub"))  # 目标在源内
    with pytest.raises(MigrationPrecheckError):
        engine.start(str(mini.tmp))  # 源在目标内
    report = precheck(r"C:\Windows\system32")
    assert not report["ok"]
    assert any("系统目录" in e for e in report["errors"])
    report = precheck("")
    assert not report["ok"]


# ── T11 空间不足 ─────────────────────────────────────────────
def test_precheck_insufficient_space(mini, monkeypatch):
    monkeypatch.setattr(storage_migration.shutil, "disk_usage",
                        lambda p: SimpleNamespace(total=10**9, free=1024, used=10**9 - 1024))
    report = precheck(str(mini.target))
    assert not report["ok"]
    assert any("空间不足" in e for e in report["errors"])


# ── T16 并发迁移拒绝 ─────────────────────────────────────────
def test_busy_rejects_second_migration(mini):
    engine = StorageMigration()
    engine._state["status"] = "running"
    with pytest.raises(MigrationBusyError):
        engine.start(str(mini.target))
    assert engine.cancel() is True
    engine._state["status"] = "idle"
    assert engine.cancel() is False


# ── T26 清理期文件占用：残留报告 + 重试清理 ──────────────────
def test_cleanup_residual_then_retry(mini):
    engine = StorageMigration()
    orig_cleanup = engine._cleanup_phase
    locked = os.path.normcase(str(mini.source / "models" / "w.pt"))
    orig_unlink = os.unlink

    def selective_unlink(path):
        if os.path.normcase(str(path)) == locked:
            raise PermissionError("模拟文件占用")
        return orig_unlink(path)

    def cleanup_with_lock(src):
        storage_migration.os.unlink = selective_unlink
        try:
            return orig_cleanup(src)
        finally:
            storage_migration.os.unlink = orig_unlink

    engine._cleanup_phase = cleanup_with_lock
    engine.start(str(mini.target))
    st = _wait(engine)
    assert st["status"] == "completed_with_warnings"
    assert any(r["path"].endswith("w.pt") for r in st["residual_files"])
    assert storage_settings.configured_root() == str(mini.target)  # 已切换，不回滚
    # 释放后重试清理
    result = engine.cleanup_old()
    assert result["residual_files"] == []
    assert not (mini.source / "models").exists()


# ── T22 空数据根 ─────────────────────────────────────────────
def test_empty_root_migration(mini):
    for name in WEB_DIRS:
        for p in (mini.source / name).rglob("*"):
            if p.is_file():
                p.unlink()
    engine = StorageMigration()
    engine.start(str(mini.target))
    st = _wait(engine)
    assert st["status"] == "completed", st.get("error")
    assert st["total_files"] == 0
    assert storage_settings.configured_root() == str(mini.target)


# ── T05 中文/空格目标路径 ────────────────────────────────────
def test_chinese_target_path(mini):
    before_core = _audit(mini.source, include_rewritable=False)
    target = mini.tmp / "目标 目录（数据盘）"
    engine = StorageMigration()
    engine.start(str(target))
    st = _wait(engine)
    assert st["status"] == "completed", st.get("error")
    assert _audit(target, include_rewritable=False) == before_core
    batches = yaml.safe_load((target / "data" / "batches.yaml").read_text(encoding="utf-8"))
    assert batches["batches"][0]["batch_name"] == "架次一"  # 中文无损


# ── T21 连续迁移 A→B→C ───────────────────────────────────────
def test_consecutive_migrations(mini):
    before_core = _audit(mini.source, include_rewritable=False)
    b = mini.tmp / "rootB"
    c = mini.tmp / "rootC"
    e1 = StorageMigration()
    e1.start(str(b))
    assert _wait(e1)["status"] == "completed"
    # 模拟重启：config 指向 B
    config.PROJECT_ROOT = b
    config.ACTIVE_ROOT = b
    e2 = StorageMigration()
    e2.start(str(c))
    assert _wait(e2)["status"] == "completed"
    assert _audit(c, include_rewritable=False) == before_core
    assert storage_settings.configured_root() == str(c)
    for name in WEB_DIRS:
        assert not (b / name).exists()


# ── D5 双形态 config/ 目录处理 ───────────────────────────────
def test_web_mode_excludes_config(mini):
    """Web 态：仓库 config/ 为 git 跟踪模板，不迁移不删除。"""
    (mini.source / "config").mkdir()
    (mini.source / "config" / "models.yaml").write_text("models: []\n", encoding="utf-8")
    engine = StorageMigration()
    engine.start(str(mini.target))
    assert _wait(engine)["status"] == "completed"
    assert (mini.source / "config" / "models.yaml").read_text(encoding="utf-8") == "models: []\n"
    assert not (mini.target / "config").exists()


def test_frozen_mode_includes_config(mini, monkeypatch):
    """冻结态：用户 config/（播种的 models.yaml）随根迁移并清理。"""
    monkeypatch.setattr(config, "FROZEN", True)
    (mini.source / "config").mkdir()
    (mini.source / "config" / "models.yaml").write_text("models: []\n", encoding="utf-8")
    engine = StorageMigration()
    engine.start(str(mini.target))
    st = _wait(engine)
    assert st["status"] == "completed", st.get("error")
    assert (mini.target / "config" / "models.yaml").read_text(encoding="utf-8") == "models: []\n"
    assert not (mini.source / "config").exists()
    assert storage_settings.anchor_path().name == "settings.yaml"
    assert storage_settings.configured_root() == str(mini.target)