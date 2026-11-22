"""存储设置服务测试：锚点三态 / 统计 / 受管清单 / 恢复态 / pending_restart。

运行：cd backend && python -m pytest tests/test_storage_settings.py -v
"""
from pathlib import Path

import pytest

import config
from core import storage_settings


@pytest.fixture
def iso(tmp_path, monkeypatch):
    """将 config 根指向临时目录（Web 形态），隔离真实仓库数据。"""
    source = tmp_path / "source"
    default = tmp_path / "default"
    source.mkdir()
    default.mkdir()
    monkeypatch.setattr(config, "PROJECT_ROOT", source)
    monkeypatch.setattr(config, "ACTIVE_ROOT", source)
    monkeypatch.setattr(config, "DEFAULT_ROOT", default)
    monkeypatch.setattr(config, "FROZEN", False)
    monkeypatch.setattr(config, "ROOT_FALLBACK_WARNING", None)
    return {"source": source, "default": default, "tmp": tmp_path}


def test_managed_dirs_web_vs_frozen(iso, monkeypatch):
    assert storage_settings.managed_dir_names() == ("data", "output", "datasets", "results", "models")
    monkeypatch.setattr(config, "FROZEN", True)
    names = storage_settings.managed_dir_names()
    assert len(names) == 6 and "config" in names
    assert storage_settings.anchor_path().name == "settings.yaml"
    monkeypatch.setattr(config, "FROZEN", False)
    assert storage_settings.anchor_path().name == "settings.local.yaml"


def test_anchor_roundtrip(iso):
    assert storage_settings.configured_root() is None
    storage_settings.write_anchor("D:\\TJZKData")
    assert storage_settings.configured_root() == "D:\\TJZKData"
    assert storage_settings.anchor_path().is_file()
    storage_settings.write_anchor(None)
    assert storage_settings.configured_root() is None


def test_anchor_corrupt_returns_empty(iso):
    storage_settings.anchor_path().write_text("data_root: [unclosed", encoding="utf-8")
    assert storage_settings.read_anchor() == {}
    assert storage_settings.configured_root() is None


def test_dir_stats(iso):
    d = iso["source"] / "data"
    d.mkdir()
    (d / "a.bin").write_bytes(b"x" * 100)
    sub = d / "sub"
    sub.mkdir()
    (sub / "b.bin").write_bytes(b"y" * 50)
    stats = storage_settings.dir_stats(d)
    assert stats == {"size_bytes": 150, "file_count": 2}
    assert storage_settings.dir_stats(iso["source"] / "missing") == {"size_bytes": 0, "file_count": 0}


def test_storage_overview_fields(iso):
    (iso["source"] / "data").mkdir()
    (iso["source"] / "data" / "f.txt").write_bytes(b"abc")
    ov = storage_settings.storage_overview()
    assert ov["active_root"] == str(iso["source"])
    assert ov["default_root"] == str(iso["default"])
    assert ov["frozen"] is False
    assert ov["is_custom"] is True
    assert ov["pending_restart"] is False
    assert ov["root_fallback_warning"] is None
    assert ov["recovery"] is None
    assert len(ov["modules"]) == 5
    data_mod = next(m for m in ov["modules"] if m["key"] == "data")
    assert data_mod["size_bytes"] == 3 and data_mod["file_count"] == 1
    assert set(ov["disk"]) == {"total", "free", "used"}


def test_pending_recovery_lifecycle(iso):
    assert storage_settings.recovery_state() is None
    storage_settings.write_pending({"migration_id": "m1", "phase": "copying",
                                    "source_root": "s", "target_root": "t"})
    rec = storage_settings.recovery_state()
    assert rec and rec["migration_id"] == "m1"
    storage_settings.write_pending({"migration_id": "m1", "phase": "completed"})
    assert storage_settings.recovery_state() is None
    storage_settings.write_pending({"migration_id": "m2", "phase": "verifying"})
    storage_settings.clear_pending()
    assert storage_settings.read_pending() == {}


def test_pending_restart_detection(iso):
    other = iso["tmp"] / "other"
    other.mkdir()
    assert storage_settings.is_pending_restart() is False
    storage_settings.write_anchor(str(other))
    assert storage_settings.is_pending_restart() is True
    # 回退警告态不报 pending（重启也无济于事，应展示警告）
    import config as _c
    _c.ROOT_FALLBACK_WARNING = "自定义数据位置不可达"
    assert storage_settings.is_pending_restart() is False


def test_pending_summary_lightweight(iso):
    s = storage_settings.storage_pending_summary()
    assert set(s) == {"pending_restart", "root_fallback_warning"}
    assert s["pending_restart"] is False