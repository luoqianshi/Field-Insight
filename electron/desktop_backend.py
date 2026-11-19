"""纯后端入口（Electron 壳用，位于 electron/desktop_backend.py）。

职责：动态端口 → 后台 HTTP 服务 → stdout 上报端口 → 等父进程结束。
不含任何 GUI 依赖（不 import webview / tkinter），供 Electron 作为子进程拉起。

约定（Electron 主进程据此解析）：
    BACKEND_PORT <port>   端口已选定
    BACKEND_READY         HTTP 服务已开始监听
父进程死亡（stdin 关闭）时自动退出，避免孤儿进程。
"""
import argparse
import os
import socket
import sys
import threading
import time

T0 = time.perf_counter()

# PyInstaller 兼容垫片：实测该 onedir 产物在部分构建参数下 sys.frozen / sys._MEIPASS 缺失，
# 会导致 config.py 退化为"源码模式"，把数据目录建到 exe 旁边、并找不到 _internal 里的资源。
_exe_dir = os.path.dirname(os.path.abspath(sys.executable))
_inner = os.path.join(_exe_dir, "_internal")
if not os.path.isdir(getattr(sys, "_MEIPASS", "")):
    if os.path.isdir(_inner):
        sys._MEIPASS = _inner
if hasattr(sys, "_MEIPASS") and sys.executable.lower().endswith(".exe"):
    if not getattr(sys, "frozen", False):
        sys.frozen = True


def _bootstrap_path():
    base = os.path.dirname(os.path.abspath(sys.argv[0]))
    candidates = []
    if getattr(sys, "frozen", False):
        candidates.append(os.path.join(getattr(sys, "_MEIPASS", base), "backend"))
    else:
        # 源码态：本文件位于 electron/，backend/ 在仓库根（electron/ 的上级）
        candidates.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))
    for c in candidates:
        if os.path.isdir(c) and c not in sys.path:
            sys.path.insert(0, c)


_bootstrap_path()


def _log(msg):
    try:
        from config import PROJECT_ROOT
        d = os.path.join(str(PROJECT_ROOT), "logs")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "backend-stdout.log"), "a", encoding="utf-8") as f:
            f.write("[%s] %7.2fs %s\n" % (time.strftime("%H:%M:%S"), time.perf_counter() - T0, msg))
    except Exception:
        pass


def _free_port(host):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind((host, 0))
        return s.getsockname()[1]
    finally:
        s.close()


def _stdin_watchdog():
    def _watch():
        try:
            while sys.stdin.readline():
                pass
        except Exception:
            pass
        os._exit(0)
    threading.Thread(target=_watch, daemon=True).start()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--no-stdin-watch", action="store_true")
    args = ap.parse_args()

    port = args.port or _free_port(args.host)
    print("BACKEND_PORT %d" % port, flush=True)

    from app import app  # 触发 create_app() + init_engines()
    _log("app imported")

    from werkzeug.serving import make_server
    server = make_server(args.host, port, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    _log("serving on %d" % port)
    print("BACKEND_READY", flush=True)

    if not args.no_stdin_watch:
        _stdin_watchdog()
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass
    server.shutdown()
    return 0


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    sys.exit(main())