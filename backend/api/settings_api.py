"""设置模块 API：存储概览 / 目标预检 / 迁移管理 / 目录选择 / 关于。

计划书：docs/sdd/plans/2026-11-20-settings-storage-migration.md §3.3
所有响应遵循统一信封：{"success": bool, "data": <data>|None, "message": str}。
"""
import os
import subprocess
import sys
import time
from pathlib import Path

from flask import Blueprint, jsonify, request

import config
from core import storage_settings
from core.storage_migration import (MigrationBusyError, MigrationError,
                                    MigrationPrecheckError, get_migration,
                                    precheck)

settings_bp = Blueprint("settings", __name__)


def _ok(data=None, message=""):
    return jsonify({"success": True, "data": data, "message": message})


def _error(message, status_code=400):
    return jsonify({"success": False, "data": None, "message": message}), status_code


# ── 存储概览 ──────────────────────────────────────────────────
@settings_bp.route("/api/settings/storage", methods=["GET"])
def storage_overview():
    """GET /api/settings/storage → 存储概览（模块占用/磁盘/恢复态）。"""
    try:
        return _ok(storage_settings.storage_overview())
    except Exception as exc:
        return _error(f"读取存储信息失败: {exc}", 500)


@settings_bp.route("/api/settings/storage/pending", methods=["GET"])
def storage_pending():
    """GET /api/settings/storage/pending → 轻量摘要（全局横幅用，不扫描目录）。"""
    return _ok(storage_settings.storage_pending_summary())


@settings_bp.route("/api/settings/storage/validate", methods=["POST"])
def validate_target():
    """POST /api/settings/storage/validate → 目标预检报告（data.ok 判定可否迁移）。"""
    body = request.get_json(silent=True) or {}
    try:
        report = precheck(body.get("target", ""))
    except Exception as exc:
        return _error(f"预检失败: {exc}", 500)
    return _ok(report)


# ── 迁移管理 ──────────────────────────────────────────────────
@settings_bp.route("/api/settings/storage/migrate", methods=["POST"])
def migrate():
    """POST /api/settings/storage/migrate → 启动迁移（409=忙，400=预检失败）。"""
    body = request.get_json(silent=True) or {}
    try:
        mid = get_migration().start(body.get("target", ""))
    except MigrationBusyError as exc:
        return _error(str(exc), 409)
    except MigrationPrecheckError as exc:
        return _error("目标预检未通过：" + "；".join(exc.errors), 400)
    except MigrationError as exc:
        return _error(str(exc), 400)
    except Exception as exc:
        return _error(f"启动迁移失败: {exc}", 500)
    return _ok({"migration_id": mid}, "迁移已启动")


@settings_bp.route("/api/settings/storage/migration", methods=["GET"])
def migration_status():
    """GET /api/settings/storage/migration → 迁移状态（前端 1s 轮询）。"""
    return _ok(get_migration().status())


@settings_bp.route("/api/settings/storage/migration/cancel", methods=["POST"])
def migration_cancel():
    """POST /api/settings/storage/migration/cancel → 协作式取消。"""
    if not get_migration().cancel():
        return _error("当前没有进行中的迁移", 409)
    return _ok(None, "已请求取消，将在当前文件完成后停止")


@settings_bp.route("/api/settings/storage/migration/resume", methods=["POST"])
def migration_resume():
    """POST /api/settings/storage/migration/resume → 中断恢复（续传/补清理）。"""
    try:
        mid = get_migration().resume()
    except MigrationBusyError as exc:
        return _error(str(exc), 409)
    except MigrationError as exc:
        return _error(str(exc), 400)
    except Exception as exc:
        return _error(f"恢复迁移失败: {exc}", 500)
    return _ok({"migration_id": mid}, "迁移已恢复")


@settings_bp.route("/api/settings/storage/migration/rollback", methods=["POST"])
def migration_rollback():
    """POST /api/settings/storage/migration/rollback → 放弃并清理目标半成品。"""
    try:
        result = get_migration().rollback()
    except MigrationBusyError as exc:
        return _error(str(exc), 409)
    except MigrationError as exc:
        return _error(str(exc), 400)
    except Exception as exc:
        return _error(f"放弃迁移失败: {exc}", 500)
    return _ok(result, "已放弃迁移，源数据完好")


@settings_bp.route("/api/settings/storage/cleanup-old", methods=["POST"])
def cleanup_old():
    """POST /api/settings/storage/cleanup-old → 重试清理旧根残留。"""
    try:
        result = get_migration().cleanup_old()
    except MigrationBusyError as exc:
        return _error(str(exc), 409)
    except MigrationError as exc:
        return _error(str(exc), 400)
    except Exception as exc:
        return _error(f"清理失败: {exc}", 500)
    return _ok(result)


@settings_bp.route("/api/settings/storage/reset-default", methods=["POST"])
def reset_default():
    """POST /api/settings/storage/reset-default → 迁回默认根。

    自定义根不可达（回退警告态）时仅清除锚点（数据保留原盘，重启后生效）。
    """
    if config.ROOT_FALLBACK_WARNING:
        storage_settings.write_anchor(None)
        return _ok({"cleared_anchor": True},
                   "已恢复默认位置（自定义位置不可达，其数据保留在原路径，重启后生效）")
    try:
        mid = get_migration().start(str(config.DEFAULT_ROOT))
    except MigrationBusyError as exc:
        return _error(str(exc), 409)
    except MigrationPrecheckError as exc:
        return _error("目标预检未通过：" + "；".join(exc.errors), 400)
    except MigrationError as exc:
        return _error(str(exc), 400)
    except Exception as exc:
        return _error(f"启动迁移失败: {exc}", 500)
    return _ok({"migration_id": mid}, "已开始迁回默认位置")


# ── 目录选择（Web 态回退；桌面态走 Electron 原生桥）────────────
@settings_bp.route("/api/settings/pick-folder", methods=["POST"])
def pick_folder():
    """POST /api/settings/pick-folder → 系统文件夹选择对话框（镜像 batches 实现）。"""
    if config.FROZEN:
        return _error("桌面态请使用原生目录选择对话框", 400)
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        return _error("当前环境未能加载系统对话框组件，请直接在输入框粘贴文件夹路径（如 D:/TJZKData）", 500)
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        folder = filedialog.askdirectory(title="选择数据保存位置")
        root.destroy()
    except Exception as exc:
        return _error(f"打开文件夹对话框失败: {exc}", 500)
    if not folder:
        return jsonify({"success": False, "data": {"cancelled": True},
                        "message": "用户取消选择"}), 200
    return _ok({"path": folder.replace("\\", "/")}, "文件夹选择成功")


# ── 打开本地目录（Web/桌面通用：后端与用户同机）────────────────
# Windows 下 explorer 新窗口受前台锁限制，会被拥有焦点的应用（桌面壳）
# 压在底层；打开后把新窗口拉到最上层，避免用户找不到。
_EXPLORER_CLASSES = ("CabinetWClass", "ExploreWClass")
_SW_RESTORE = 9
_SWP_NOSIZE = 0x0001
_SWP_NOMOVE = 0x0002
_SWP_SHOWWINDOW = 0x0040
_VK_MENU = 0x12  # ALT 键：模拟按键事件解锁 SetForegroundWindow 前台权限


def _user32():
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    # 64 位 HWND 需按指针宽度传参，声明 argtypes 防整型截断
    user32.EnumWindows.argtypes = [ctypes.WINFUNCTYPE(
        wintypes.BOOL, wintypes.HWND, wintypes.LPARAM), wintypes.LPARAM]
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND,
                                    ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                    ctypes.c_int, ctypes.c_uint]
    user32.keybd_event.argtypes = [wintypes.BYTE, wintypes.BYTE,
                                   wintypes.DWORD, ctypes.c_void_p]
    return user32


def _explorer_handles() -> set:
    """枚举当前所有资源管理器文件夹窗口的 HWND 集合。"""
    import ctypes
    from ctypes import wintypes
    user32 = _user32()
    found = set()
    callback_t = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def _cb(hwnd, _lparam):
        buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(int(hwnd), buf, 256)
        if buf.value in _EXPLORER_CLASSES:
            found.add(int(hwnd))
        return True

    user32.EnumWindows(callback_t(_cb), 0)
    return found


def _raise_explorer_window(hwnd: int) -> None:
    """把指定资源管理器窗口恢复并置顶到最上层（含前台激活）。"""
    user32 = _user32()
    user32.ShowWindow(hwnd, _SW_RESTORE)
    # 前台锁：先试直接激活；失败则模拟 ALT 按键事件获得前台切换权限后重试
    if not user32.SetForegroundWindow(hwnd):
        user32.keybd_event(_VK_MENU, 0, 0, 0)
        try:
            user32.SetForegroundWindow(hwnd)
        finally:
            user32.keybd_event(_VK_MENU, 0, 2, 0)
    user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0,
                        _SWP_NOMOVE | _SWP_NOSIZE | _SWP_SHOWWINDOW)


def _raise_new_explorer_window(before: set, timeout_s: float = 2.0) -> None:
    """等待新打开的资源管理器窗口出现并置顶；找不到则静默放弃（不影响打开）。"""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        new = _explorer_handles() - before
        if new:
            _raise_explorer_window(max(new))  # 句柄值随创建时间递增，取最新
            return
        time.sleep(0.05)


def _open_in_file_manager(target: Path) -> None:
    """用系统文件管理器打开目录（Windows/macOS/Linux），Windows 下窗口置顶。"""
    if sys.platform.startswith("win"):
        before = _explorer_handles()
        os.startfile(str(target))  # type: ignore[attr-defined]
        try:
            _raise_new_explorer_window(before)
        except Exception:
            pass  # 置顶失败不影响目录打开
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(target)])
    else:
        subprocess.Popen(["xdg-open", str(target)])


@settings_bp.route("/api/settings/open-folder", methods=["POST"])
def open_folder():
    """POST /api/settings/open-folder → 打开受管目录（body: {"key": "root" | "data" | ...}）。

    只接受受管目录标识，路径由后端解析，避免前端传入任意路径被直接执行。
    """
    body = request.get_json(silent=True) or {}
    key = str(body.get("key") or "").strip()
    if key == "root":
        target = Path(config.PROJECT_ROOT)
    elif key in storage_settings.managed_dir_names():
        target = Path(config.PROJECT_ROOT) / key
    else:
        return _error("未知目录标识", 400)
    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return _error(f"目录不可用: {exc}", 400)
    try:
        _open_in_file_manager(target)
    except Exception as exc:
        return _error(f"打开目录失败: {exc}", 500)
    return _ok({"path": str(target)}, "已在文件管理器中打开")


# ── 关于 ──────────────────────────────────────────────────────
@settings_bp.route("/api/settings/about", methods=["GET"])
def about():
    """GET /api/settings/about → 轻量关于信息（F14）。"""
    # 版本单一来源：config.APP_VERSION（桌面冻结态由 Electron 壳经环境变量透传）
    return _ok({
        "app": "田间智瞰",
        "version": config.APP_VERSION,
        "mode": "desktop" if config.FROZEN else "web",
        "data_root": str(config.PROJECT_ROOT),
        "python": sys.version.split()[0],
    })