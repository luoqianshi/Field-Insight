# -*- mode: python ; coding: utf-8 -*-
"""纯后端冻结 spec（Electron 载荷用，位于 electron/desktop_backend.spec）。

资源经 SPECPATH 锚定仓库根，与构建 cwd 无关
（消除旧版"cwd 必须是 D:\\UAVDesktopBuild\\app"的约束）。
- 入口：electron/desktop_backend.py（无窗口）
- 不收集 webview / clr_loader / tkinter，减小体积并避免拉起 GUI
"""
import os
import sys

from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
BACKEND = os.path.join(ROOT, "backend")

# collect_submodules 在 spec 求值期导入 api/core，需显式把 backend 加入 sys.path
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

datas = [
    (os.path.join(ROOT, "backend", "static"), "backend/static"),
    (os.path.join(ROOT, "config"), "config"),
    (os.path.join(ROOT, "models"), "models"),
]
binaries = []
hiddenimports = collect_submodules("api") + collect_submodules("core")

for pkg in ("ultralytics",):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception as exc:
        print("collect_all failed:", pkg, exc)

a = Analysis(
    [os.path.join(SPECPATH, "desktop_backend.py")],
    pathex=[ROOT, BACKEND],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "webview", "clr_loader", "pythonnet", "tkinter", "_tkinter",
        "PyQt5", "PySide2", "PySide6", "IPython", "notebook",
        "jupyter", "pytest", "sphinx", "flask_cors",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="TianJianZhiKanBackend",
    icon=os.path.join(SPECPATH, "build", "app.ico"),
    console=True,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="TianJianZhiKanBackend",
)