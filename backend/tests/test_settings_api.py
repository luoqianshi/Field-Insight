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


def test_open_in_file_manager_focuses_new_explorer_window(monkeypatch):
    """Windows：打开目录后应把新资源管理器窗口置顶，而不是丢在应用窗口底层。"""
    calls = {"startfile": [], "raise": []}
    seq = iter([{100, 200}, {100, 200, 250}])  # 打开前后两次枚举：出现新句柄 250
    monkeypatch.setattr("api.settings_api._explorer_handles", lambda: next(seq))
    monkeypatch.setattr("api.settings_api.os.startfile",
                        lambda p: calls["startfile"].append(p))
    monkeypatch.setattr("api.settings_api._raise_new_explorer_window",
                        lambda before, timeout_s=2.0: calls["raise"].append(before))
    monkeypatch.setattr("api.settings_api.sys.platform", "win32")

    from api.settings_api import _open_in_file_manager
    from pathlib import Path
    target = Path("D:/data")
    _open_in_file_manager(target)
    assert calls["startfile"] == [str(target)]
    # 置顶基准应是打开前的句柄集合 {100, 200}，从而识别出新窗口 250
    assert calls["raise"] == [{100, 200}]


def test_raise_new_explorer_window_picks_new_handle(monkeypatch):
    from api.settings_api import _raise_new_explorer_window
    raised = []
    monkeypatch.setattr("api.settings_api._explorer_handles", lambda: {100, 250, 300})
    monkeypatch.setattr("api.settings_api._raise_explorer_window",
                        lambda hwnd: raised.append(hwnd))
    _raise_new_explorer_window({100, 250}, timeout_s=1.0)
    assert raised == [300]  # 只置顶新出现的句柄


def test_raise_new_explorer_window_timeout_is_silent(monkeypatch):
    """找不到新窗口（如复用已有窗口）时静默返回，不影响打开行为。"""
    from api.settings_api import _raise_new_explorer_window
    monkeypatch.setattr("api.settings_api._explorer_handles", lambda: {100})
    monkeypatch.setattr("api.settings_api._raise_explorer_window",
                        lambda hwnd: pytest.fail("不应置顶已有窗口"))
    _raise_new_explorer_window({100}, timeout_s=0.2)


def test_raise_explorer_window_alt_fallback():
    """SetForegroundWindow 被前台锁拒绝时，用 ALT 模拟按键解锁后重试。"""
    from api import settings_api

    class FakeUser32:
        def __init__(self):
            self.calls = []
            self.foreground_tried = 0

        def ShowWindow(self, hwnd, cmd):
            self.calls.append(("show", hwnd, cmd))

        def SetForegroundWindow(self, hwnd):
            self.foreground_tried += 1
            self.calls.append(("fg", hwnd, self.foreground_tried))
            return 0 if self.foreground_tried == 1 else 1  # 首次失败，重试成功

        def keybd_event(self, vk, scan, flags, extra):
            self.calls.append(("key", vk, flags))

        def SetWindowPos(self, hwnd, after, x, y, cx, cy, flags):
            self.calls.append(("pos", hwnd, flags))

    fake = FakeUser32()
    orig = settings_api._user32
    settings_api._user32 = lambda: fake
    try:
        settings_api._raise_explorer_window(250)
    finally:
        settings_api._user32 = orig

    kinds = [c[0] for c in fake.calls]
    assert kinds == ["show", "fg", "key", "fg", "key", "pos"]
    # ALT 按下（flags=0）→ 重试 → ALT 释放（flags=2）
    assert fake.calls[2] == ("key", settings_api._VK_MENU, 0)
    assert fake.calls[4] == ("key", settings_api._VK_MENU, 2)
    assert fake.calls[-1][2] == (settings_api._SWP_NOMOVE
                                 | settings_api._SWP_NOSIZE
                                 | settings_api._SWP_SHOWWINDOW)


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