import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse, JSONResponse
from a2wsgi import WSGIMiddleware

from loadSettings import loadSettings, SETTINGS_PATH, DATA_DIR
from getGlobalLogger import logger

BIND_HOST = loadSettings("BIND_HOST")
PORT = int(loadSettings("PORT"))
WEBDAV_MOUNT_PATH = loadSettings("WEBDAV_MOUNT_PATH") or "/dav"

app = FastAPI(
    title="123Pan Unlimited (merged)",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


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


_check_insecure_defaults()

# WebDAV 路由必须先注册，才能优先于挂到 "/" 的 Flask 面板匹配
from webdav_router import router as webdav_router  # noqa: E402

app.include_router(webdav_router, prefix=WEBDAV_MOUNT_PATH)

# 少数客户端不会自动补末尾斜杠
_MOUNT_NO_SLASH = WEBDAV_MOUNT_PATH.rstrip("/")


@app.get(_MOUNT_NO_SLASH, include_in_schema=False)
def _webdav_root_redirect():
    return RedirectResponse(url=WEBDAV_MOUNT_PATH + "/", status_code=307)


@app.get("/healthz", include_in_schema=False)
def _healthz():
    return JSONResponse(
        {
            "status": "ok",
            "dataDir": DATA_DIR,
            "settings": SETTINGS_PATH,
            "webdav": f"http://{BIND_HOST}:{PORT}{WEBDAV_MOUNT_PATH}",
            "vfsLoaded": "file_system" in sys.modules
            and getattr(sys.modules["file_system"], "_vfs", None) is not None,
        }
    )


# Flask 面板（分享导出、搜索、管理后台）挂在根路径
import web  # noqa: E402

app.mount("/", WSGIMiddleware(web.app))


logger.info(f"配置文件: {SETTINGS_PATH}")
logger.info(f"数据目录: {DATA_DIR}")
logger.info(f"网页面板: http://{BIND_HOST}:{PORT}/  (管理后台 /{loadSettings('ADMIN_ENTRY')}/login)")
logger.info(f"WebDAV:   http://{BIND_HOST}:{PORT}{WEBDAV_MOUNT_PATH}")


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=BIND_HOST,
        port=PORT,
        log_level="warning",
        access_log=False,
        timeout_graceful_shutdown=5,
    )
