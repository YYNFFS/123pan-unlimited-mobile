import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import jsonify, redirect

from loadSettings import DATA_DIR, SETTINGS_PATH, loadSettings
from getGlobalLogger import logger

BIND_HOST = loadSettings("BIND_HOST")
PORT = int(loadSettings("PORT"))
WEBDAV_MOUNT_PATH = loadSettings("WEBDAV_MOUNT_PATH") or "/dav"


def _check_insecure_defaults():
    """局域网暴露的服务不允许沿用出厂密码。"""
    if BIND_HOST in ("127.0.0.1", "localhost", "::1"):
        return
    weak = [
        key
        for key, default in (
            ("WEBDAV_PASSWORD", "123456"),
            ("ADMIN_PASSWORD", "123456"),
        )
        if str(loadSettings(key)) == default
    ]
    if weak:
        raise SystemExit(
            f"检测到仍在使用默认密码（{', '.join(weak)}），且监听 {BIND_HOST}:{PORT}。\n"
            f"局域网内其他设备可以直接登录你的网盘账号，请先修改 {SETTINGS_PATH} 里的密码，"
            f"或把 BIND_HOST 改成 127.0.0.1 仅本机访问。"
        )


def create_app():
    """把 WebDAV 蓝图挂到面板同一个 Flask 应用上。"""
    import web  # 面板路由，import 时即完成注册
    from webdav import webdav_bp

    _check_insecure_defaults()

    web.app.register_blueprint(webdav_bp, url_prefix=WEBDAV_MOUNT_PATH)

    @web.app.get("/healthz")
    def _healthz():
        import file_system

        return jsonify(
            {
                "status": "ok",
                "dataDir": DATA_DIR,
                "settings": SETTINGS_PATH,
                "webdav": f"http://{BIND_HOST}:{PORT}{WEBDAV_MOUNT_PATH}",
                "vfsLoaded": getattr(file_system, "_vfs", None) is not None,
            }
        )

    # 少数客户端不会自动补末尾斜杠
    @web.app.get(WEBDAV_MOUNT_PATH.rstrip("/"))
    def _webdav_root_redirect():
        return redirect(WEBDAV_MOUNT_PATH + "/", code=307)

    return web.app


app = create_app()

logger.info(f"配置文件: {SETTINGS_PATH}")
logger.info(f"数据目录: {DATA_DIR}")
logger.info(
    f"网页面板: http://{BIND_HOST}:{PORT}/  (管理后台 /{loadSettings('ADMIN_ENTRY')}/login)"
)
logger.info(f"WebDAV:   http://{BIND_HOST}:{PORT}{WEBDAV_MOUNT_PATH}")


def serve(host=None, port=None):
    """用纯 Python 的 waitress 启动，避免任何 C 扩展依赖（Android 上必需）。"""
    host = BIND_HOST if host is None else host
    port = PORT if port is None else int(port)
    try:
        from waitress import serve as _waitress_serve
    except ImportError:
        logger.warning("未安装 waitress，退回 Werkzeug 开发服务器（仅适合调试）")
        from werkzeug.serving import run_simple

        run_simple(host, port, app, threaded=True)
        return
    logger.info(f"waitress 已启动: http://{host}:{port}/")
    _waitress_serve(app, host=host, port=port, threads=8, ident="123pan")


if __name__ == "__main__":
    serve()
