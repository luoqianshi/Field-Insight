"""设置 API 测试：Flask test client 验证全端点信封/状态码/迁移闭环。

运行：cd backend && python -m pytest tests/test_settings_api.py -v
"""
import time
from types import SimpleNamespace

import pytest

import config
from core import storage_migration, storage_settings


@pytest.fixture(scope="module")
def app():
    from app import create_app
    return create_app()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def iso(tmp_path, monkeypatch):
    """临时数据根 + 全新迁移单例（隔离真实仓库数据与跨测试状态）。"""
    source = tmp_path / "source"
    default = tmp_path / "default"
    target = tmp_path / "target"
    (source / "data").mkdir(parents=True)
    (source / "data" / "f.txt").write_bytes(b"hello-settings")
    default.mkdir()
    monkeypatch.setattr(config, "PROJECT_ROOT", source)
    monkeypatch.setattr(config, "ACTIVE_ROOT", source)
    monkeypatch.setattr(config, "DEFAULT_ROOT", default)
    monkeypatch.setattr(config, "FROZEN", False)
    monkeypatch.setattr(config, "ROOT_FALLBACK_WARNING", None)
    monkeypatch.setattr(storage_migration, "_migration", None)
    return SimpleNamespace(source=source, default=default, target=target)


def _poll_until_done(client, timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        body = client.get("/api/settings/storage/migration").get_json()
        assert body["success"] is True
        if body["data"]["status"] != "running":
            return body["data"]
        time.sleep(0.05)
    pytest.fail("迁移超时未结束")


def test_storage_overview_envelope(client, iso):
    resp = client.get("/api/settings/storage")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    data = body["data"]
    assert data["active_root"] == str(iso.source)
    assert data["frozen"] is False
    assert len(data["modules"]) == 5
    assert data["recovery"] is None


def test_storage_pending_endpoint(client, iso):
    body = client.get("/api/settings/storage/pending").get_json()
    assert body["success"] is True
    assert body["data"] == {"pending_restart": False, "root_fallback_warning": None}


def test_validate_ok_and_nested(client, iso):
    body = client.post("/api/settings/storage/validate",
                       json={"target": str(iso.target)}).get_json()
    assert body["success"] is True
    assert body["data"]["ok"] is True
    assert body["data"]["source_file_count"] == 1
    body = client.post("/api/settings/storage/validate",
                       json={"target": str(iso.source / "data" / "sub")}).get_json()
    assert body["data"]["ok"] is False
    assert body["data"]["errors"]


def test_migrate_poll_complete(client, iso):
    resp = client.post("/api/settings/storage/migrate", json={"target": str(iso.target)})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert body["data"]["migration_id"]
    st = _poll_until_done(client)
    assert st["status"] == "completed", st.get("error")
    assert (iso.target / "data" / "f.txt").read_bytes() == b"hello-settings"
    assert not (iso.source / "data").exists()
    # Web 态：锚点已切换但进程未重启 → pending_restart
    ov = client.get("/api/settings/storage").get_json()["data"]
    assert ov["pending_restart"] is True
    assert ov["configured_root"] == str(iso.target)


def test_migrate_busy_409(client, iso, monkeypatch):
    class _Busy:
        def start(self, target, resume=False):
            raise storage_migration.MigrationBusyError("迁移进行中，请等待完成")

    monkeypatch.setattr("api.settings_api.get_migration", lambda: _Busy())
    resp = client.post("/api/settings/storage/migrate", json={"target": str(iso.target)})
    assert resp.status_code == 409
    assert resp.get_json()["success"] is False


def test_migrate_precheck_400(client, iso):
    resp = client.post("/api/settings/storage/migrate", json={"target": str(iso.source)})
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["success"] is False
    assert "预检未通过" in body["message"]


def test_cancel_without_migration_409(client, iso):
    resp = client.post("/api/settings/storage/migration/cancel")
    assert resp.status_code == 409


def test_rollback_without_migration_400(client, iso):
    resp = client.post("/api/settings/storage/migration/rollback")
    assert resp.status_code == 400


def test_resume_without_pending_400(client, iso):
    resp = client.post("/api/settings/storage/migration/resume")
    assert resp.status_code == 400


def test_pick_folder_frozen_guard(client, iso, monkeypatch):
    monkeypatch.setattr(config, "FROZEN", True)
    resp = client.post("/api/settings/pick-folder")
    body = resp.get_json()
    assert body["success"] is False
    assert "原生" in body["message"]


def test_open_folder_rejects_unknown_key(client, iso):
    for key in ("", "../etc", "static"):
        resp = client.post("/api/settings/open-folder", json={"key": key})
        assert resp.status_code == 400
        assert resp.get_json()["success"] is False


def test_open_folder_opens_managed_dir(client, iso, monkeypatch):
    opened = []
    monkeypatch.setattr("api.settings_api._open_in_file_manager",
                        lambda p: opened.append(str(p)))
    body = client.post("/api/settings/open-folder", json={"key": "output"}).get_json()
    assert body["success"] is True
    assert body["data"]["path"] == str(iso.source / "output")
    assert opened == [str(iso.source / "output")]
    assert (iso.source / "output").is_dir()

    body = client.post("/api/settings/open-folder", json={"key": "root"}).get_json()
    assert body["data"]["path"] == str(iso.source)

    # 冻结态多出的 config 目录同样可打开
    monkeypatch.setattr(config, "FROZEN", True)
    body = client.post("/api/settings/open-folder", json={"key": "config"}).get_json()
    assert body["success"] is True


def test_about(client, iso):
    body = client.get("/api/settings/about").get_json()
    assert body["success"] is True
    data = body["data"]
    assert data["app"] == "田间智瞰"
    assert data["mode"] == "web"
    assert data["data_root"] == str(iso.source)
    assert data["python"]


def test_reset_default_fallback_clears_anchor(client, iso, monkeypatch):
    storage_settings.write_anchor(str(iso.target))
    monkeypatch.setattr(config, "ROOT_FALLBACK_WARNING", "自定义数据位置不可达")
    resp = client.post("/api/settings/storage/reset-default")
    body = resp.get_json()
    assert body["success"] is True
    assert body["data"]["cleared_anchor"] is True
    assert storage_settings.configured_root() is None


def test_reset_default_starts_migration(client, iso):
    storage_settings.write_anchor(str(iso.target))
    # 先把数据迁到 target（模拟自定义态），再迁回默认
    client.post("/api/settings/storage/migrate", json={"target": str(iso.target)})
    _poll_until_done(client)
    config.PROJECT_ROOT = iso.target
    config.ACTIVE_ROOT = iso.target
    resp = client.post("/api/settings/storage/reset-default")
    assert resp.status_code == 200
    assert resp.get_json()["data"]["migration_id"]
    st = _poll_until_done(client)
    assert st["status"] == "completed", st.get("error")
    assert (iso.default / "data" / "f.txt").read_bytes() == b"hello-settings"
    assert storage_settings.configured_root() == str(iso.default)