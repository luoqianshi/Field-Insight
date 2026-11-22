"""设置模块 API：存储概览 / 目标预检 / 迁移管理 / 目录选择 / 关于。

计划书：docs/sdd/plans/2026-11-20-settings-storage-migration.md §3.3
所有响应遵循统一信封：{"success": bool, "data": <data>|None, "message": str}。
"""
import sys
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


# ── 关于 ──────────────────────────────────────────────────────
@settings_bp.route("/api/settings/about", methods=["GET"])
def about():
    """GET /api/settings/about → 轻量关于信息（F14）。"""
    version = None
    if not config.FROZEN:
        # 版本单一来源 electron/package.json（开发态可读；冻结态不收集该文件）
        try:
            import json
            pkg = Path(config.DEFAULT_ROOT) / "electron" / "package.json"
            version = json.loads(pkg.read_text(encoding="utf-8")).get("version")
        except Exception:
            version = None
    return _ok({
        "app": "田间智瞰",
        "version": version,
        "mode": "desktop" if config.FROZEN else "web",
        "data_root": str(config.PROJECT_ROOT),
        "python": sys.version.split()[0],
    })