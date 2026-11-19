"""全局配置：路径与常量。

Electron 桌面端双根配置（FROZEN 门控，非冻结态与 Web 开发行为一致）：
- RESOURCE_ROOT：只读资源（backend/static、config 模板、内置权重）
- PROJECT_ROOT：可写数据根（data/output/datasets/results/config）
"""
import os
import shutil
import sys
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)


def _resource_root() -> Path:
    if FROZEN:
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def _user_root() -> Path:
    if not FROZEN:
        return Path(__file__).resolve().parent.parent
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / "TianJianZhiKan"


RESOURCE_ROOT = _resource_root()
PROJECT_ROOT = _user_root()

BACKEND_DIR = RESOURCE_ROOT / "backend"
MODELS_DIR = PROJECT_ROOT / "models"
CONFIG_DIR = PROJECT_ROOT / "config"
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