"""全局配置：路径与常量。

Electron 桌面端双根配置（FROZEN 门控，非冻结态与 Web 开发行为一致）：
- RESOURCE_ROOT：只读资源（backend/static、config 模板、内置权重）
- PROJECT_ROOT：可写数据根（data/output/datasets/results/config）

存储位置自定义（设置模块，docs/sdd/plans/2026-11-20-settings-storage-migration.md）：
- 锚点文件永不随数据迁移：冻结态 DEFAULT_ROOT/settings.yaml，非冻结态 DEFAULT_ROOT/settings.local.yaml
- 锚点 data_root 为合法绝对路径且可达 → 覆盖 PROJECT_ROOT；否则回退默认根并记录 ROOT_FALLBACK_WARNING
- 各模块在导入时捕获路径常量，故自定义根在「迁移 + 重启后端」后生效
"""
import json
import os
import shutil
import sys
from pathlib import Path

import yaml

FROZEN = getattr(sys, "frozen", False)


def _resource_root() -> Path:
    if FROZEN:
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def _default_root() -> Path:
    if not FROZEN:
        return Path(__file__).resolve().parent.parent
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / "TianJianZhiKan"


RESOURCE_ROOT = _resource_root()
DEFAULT_ROOT = _default_root()


def _app_version() -> str:
    """应用版本单一来源 electron/package.json；桌面冻结态由壳经环境变量透传。"""
    env_version = os.environ.get("TJZK_APP_VERSION")
    if env_version:
        return env_version
    try:
        pkg = Path(__file__).resolve().parent.parent / "electron" / "package.json"
        return json.loads(pkg.read_text(encoding="utf-8")).get("version") or "0.5.8"
    except Exception:
        return "0.5.8"


APP_VERSION = _app_version()

# 锚点文件：始终留守默认根（KB 级），不随业务数据迁移
ANCHOR_PATH = DEFAULT_ROOT / ("settings.yaml" if FROZEN else "settings.local.yaml")

ROOT_FALLBACK_WARNING = None  # 自定义根不可达/损坏时的警告（供设置 API 暴露）
CONFIGURED_ROOT = None        # 启动时锚点 data_root 原始值（None = 默认）


def _load_anchor_root():
    """读取锚点 data_root；损坏/非法时返回 None 并记录警告。"""
    global ROOT_FALLBACK_WARNING, CONFIGURED_ROOT
    if not ANCHOR_PATH.is_file():
        return None
    try:
        data = yaml.safe_load(ANCHOR_PATH.read_text(encoding="utf-8"))
    except Exception:
        ROOT_FALLBACK_WARNING = "存储配置损坏，已恢复默认位置"
        return None
    raw = data.get("data_root") if isinstance(data, dict) else None
    if raw is None or not str(raw).strip():
        return None
    CONFIGURED_ROOT = str(raw).strip()
    p = Path(CONFIGURED_ROOT)
    if not p.is_absolute():
        ROOT_FALLBACK_WARNING = "存储配置路径非法，已恢复默认位置"
        return None
    return p


def _user_root() -> Path:
    global ROOT_FALLBACK_WARNING
    configured = _load_anchor_root()
    if configured is None:
        return DEFAULT_ROOT
    try:
        if configured.is_dir():
            return configured
        anchor = configured.anchor
        if anchor and not Path(anchor).exists():
            ROOT_FALLBACK_WARNING = f"自定义数据位置不可达（{configured}），已临时使用默认位置"
        else:
            ROOT_FALLBACK_WARNING = f"自定义数据目录不存在（{configured}），已临时使用默认位置"
    except OSError:
        ROOT_FALLBACK_WARNING = f"自定义数据位置不可达（{configured}），已临时使用默认位置"
    return DEFAULT_ROOT


PROJECT_ROOT = _user_root()
ACTIVE_ROOT = PROJECT_ROOT  # 本进程实际生效根（与锚点比对判定 pending_restart）

BACKEND_DIR = RESOURCE_ROOT / "backend"
MODELS_DIR = PROJECT_ROOT / "models"
# config/ 特例（决策 D5）：非冻结态为 git 跟踪的模板目录（RESOURCE_ROOT==PROJECT_ROOT），不随数据根迁移
CONFIG_DIR = (PROJECT_ROOT / "config") if FROZEN else (DEFAULT_ROOT / "config")
RESULTS_DIR = PROJECT_ROOT / "results"
MOCK_DIR = BACKEND_DIR / "mock"
MOCK_IMAGES_DIR = RESOURCE_ROOT / "mock"
STATIC_DIR = BACKEND_DIR / "static"
MODELS_YAML = CONFIG_DIR / "models.yaml"

# ── 数据管理（架次注册）─────────────────────────────────────────────
DATA_DIR = PROJECT_ROOT / "data"
BATCHES_YAML = DATA_DIR / "batches.yaml"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
MAX_IMAGES_PER_BATCH = 2000
MAX_IMAGE_SIZE_BYTES = 50 * 1024 * 1024  # 50MB
THUMBNAIL_MAX_SIZE = 400
PREVIEW_MEDIUM_SIZE = 1920
CROP_NAME_MAP = {"sugarcane": "甘蔗", "corn": "玉米", "wheat": "小麦", "rice": "水稻"}
DEFAULT_DRONE_MODEL = "DJI Mavic 3 M"
DEFAULT_OVERLAP_FRONT = 0.8
DEFAULT_OVERLAP_SIDE = 0.7

HOST = "127.0.0.1" if FROZEN else "0.0.0.0"
PORT = int(os.environ.get("UAV_PORT", "5000"))
DEBUG = False if FROZEN else True
MAX_WORKERS = 1       # PRD: 并发=1
LRU_CACHE_SIZE = 3    # 引擎实例缓存上限

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

# 冻结形态下，把内置的 YAML 模板播种到用户目录（仅缺失时）
if FROZEN:
    for _name in ("models.yaml",):
        _target = CONFIG_DIR / _name
        _source = RESOURCE_ROOT / "config" / _name
        if not _target.exists() and _source.exists():
            shutil.copy2(str(_source), str(_target))

# ── 数据处理（模块二）─────────────────────────────────────────────
OUTPUT_DIR = PROJECT_ROOT / "output"
PROCESSING_TASKS_YAML = DATA_DIR / "processing_tasks.yaml"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── 数据集管理（模块三）─────────────────────────────────────────────
DATASETS_DIR = PROJECT_ROOT / "datasets"
DATASETS_YAML = DATASETS_DIR / "datasets.yaml"
DATASETS_DIR.mkdir(parents=True, exist_ok=True)