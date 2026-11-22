"""存储设置服务：锚点读写、存储统计、受管目录清单、中断恢复态。

计划书：docs/sdd/plans/2026-11-20-settings-storage-migration.md
- 锚点文件留守默认根（冻结态 settings.yaml / 非冻结态 settings.local.yaml），KB 级，不随数据迁移
- 受管目录：冻结态 6 个（含 config），非冻结态 5 个（仓库 config/ 为 git 跟踪模板，决策 D5）
- 所有函数动态读取 config 模块属性（支持测试 monkeypatch）
"""
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

import yaml

import config

MANAGED_DIRS_FROZEN = ("data", "output", "datasets", "results", "models", "config")
MANAGED_DIRS_WEB = ("data", "output", "datasets", "results", "models")

MODULE_LABELS = {
    "data": "数据管理",
    "output": "数据处理",
    "datasets": "数据集管理",
    "results": "算法结果",
    "models": "模型权重",
    "config": "模型注册表",
}

PENDING_FILENAME = "migration_pending.json"


def anchor_path() -> Path:
    return Path(config.DEFAULT_ROOT) / ("settings.yaml" if config.FROZEN else "settings.local.yaml")


def pending_path() -> Path:
    return Path(config.DEFAULT_ROOT) / PENDING_FILENAME


def managed_dir_names():
    return MANAGED_DIRS_FROZEN if config.FROZEN else MANAGED_DIRS_WEB


def managed_dirs(root=None):
    base = Path(root) if root is not None else Path(config.PROJECT_ROOT)
    return [base / name for name in managed_dir_names()]


def read_anchor() -> dict:
    p = anchor_path()
    if not p.is_file():
        return {}
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def configured_root():
    """实时读取锚点 data_root（迁移切换后运行中进程也能感知 pending_restart）。"""
    raw = read_anchor().get("data_root")
    if raw is None or not str(raw).strip():
        return None
    return str(raw).strip()


def write_anchor(data_root) -> None:
    """原子写锚点；data_root=None 清除自定义配置（恢复默认）。"""
    p = anchor_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    data = read_anchor()
    if data_root is None:
        data.pop("data_root", None)
    else:
        data["data_root"] = str(data_root)
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    tmp = p.with_suffix(".yaml.tmp")
    tmp.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    os.replace(str(tmp), str(p))


def dir_stats(path) -> dict:
    size = 0
    count = 0
    path = Path(path)
    if path.is_dir():
        for root, _dirs, files in os.walk(str(path)):
            for f in files:
                try:
                    size += os.path.getsize(os.path.join(root, f))
                    count += 1
                except OSError:
                    pass
    return {"size_bytes": size, "file_count": count}


def disk_info(path) -> dict:
    try:
        usage = shutil.disk_usage(str(path))
        return {"total": usage.total, "free": usage.free, "used": usage.used}
    except OSError:
        return {"total": 0, "free": 0, "used": 0}


def is_pending_restart() -> bool:
    cfg = configured_root()
    if not cfg or config.ROOT_FALLBACK_WARNING:
        return False
    return os.path.normcase(cfg) != os.path.normcase(str(config.ACTIVE_ROOT))


def read_pending() -> dict:
    p = pending_path()
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def write_pending(info: dict) -> None:
    p = pending_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(str(tmp), str(p))


def clear_pending() -> None:
    try:
        pending_path().unlink()
    except OSError:
        pass


def recovery_state():
    """启动中断恢复态：pending 存在且未完成 → 恢复对象（供设置页恢复卡片）。"""
    info = read_pending()
    if not info or info.get("phase") == "completed":
        return None
    return info


def storage_overview() -> dict:
    active = Path(config.PROJECT_ROOT)
    modules = []
    for name in managed_dir_names():
        d = active / name
        stats = dir_stats(d)
        modules.append({"key": name, "label": MODULE_LABELS.get(name, name),
                        "dir": str(d), **stats})
    return {
        "active_root": str(active),
        "configured_root": configured_root(),
        "default_root": str(config.DEFAULT_ROOT),
        "frozen": bool(config.FROZEN),
        "is_custom": os.path.normcase(str(active)) != os.path.normcase(str(config.DEFAULT_ROOT)),
        "pending_restart": is_pending_restart(),
        "root_fallback_warning": config.ROOT_FALLBACK_WARNING,
        "modules": modules,
        "disk": disk_info(active),
        "recovery": recovery_state(),
    }


def storage_pending_summary() -> dict:
    """轻量摘要（不扫描目录）：供全局横幅轮询。"""
    return {
        "pending_restart": is_pending_restart(),
        "root_fallback_warning": config.ROOT_FALLBACK_WARNING,
    }