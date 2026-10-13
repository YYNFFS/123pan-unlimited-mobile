# -*- coding: utf-8 -*-
"""Android 端唯一入口，由 Kotlin 通过 Chaquopy 调用。

约定：出入参一律用 JSON 字符串，避免跨语言传递复杂对象。
配置在 loadSettings 里是进程级缓存，所以改完 settings.yaml 必须走 restart()，
由 _purge_app_modules() 丢掉业务模块、按新配置重建 Flask 应用。
"""

import json
import os
import secrets
import socket
import string
import sys
import threading
import traceback

APP_DIR = os.path.dirname(os.path.abspath(__file__))
_LOCK = threading.RLock()
_SERVER = None
_THREAD = None
_RUNTIME = {"host": "", "port": 0}

# 首次运行时写出的配置：默认只监听回环，由用户在设置页主动打开局域网共享
_DEFAULT_SETTINGS = {
    "BIND_HOST": "127.0.0.1",
    "PORT": 33333,
    "WEBDAV_MOUNT_PATH": "/dav",
    "WEBDAV_USERNAME": "admin",
    "WEBDAV_PASSWORD": "123456",
    "123PAN_USERNAME": "",
    "123PAN_PASSWORD": "",
    "WEBDAV_FALLBACK_URL": "",
    "DATABASE_PATH": "data/PAN123DATABASE.db",
    "SPLIT_FOLDER": False,
    "ADMIN_ENTRY": "",
    "ADMIN_USERNAME": "admin",
    "ADMIN_PASSWORD": "123456",
    "SECRET_KEY": "",
    "TASK_QUEUE_TIMEOUT_SECONDS": 600,
    "LOG_DIR": "logs",
    "LOGGING_LEVEL": "INFO",
    "BAN_IP": False,
    "CHANNEL_NAME": "",
    "MESSAGE_AFTER_ID": 8050,
    "REQUEST_TIMEOUT_SECONDS": 30,
}

# 沿用出厂密码时不允许对局域网开放，和 server.py 的守卫保持一致
_DEFAULT_SECRETS = {"WEBDAV_PASSWORD": "123456", "ADMIN_PASSWORD": "123456"}


def _json(**kwargs):
    return json.dumps(kwargs, ensure_ascii=False)


def _random_token(length=10):
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _lan_ip():
    """取手机在局域网里的地址：UDP connect 不真的发包，只是选出出口网卡。"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except Exception:  # noqa: BLE001
        return ""
    finally:
        sock.close()


def _settings_path(data_dir):
    return os.path.abspath(os.path.join(data_dir, "settings.yaml"))


def _data_dir():
    return os.environ.get("PAN123_DATA_DIR") or ""


def _ensure_settings_file(data_dir):
    path = _settings_path(data_dir)
    if os.path.exists(path):
        return path
    import yaml

    settings = dict(_DEFAULT_SETTINGS)
    settings["ADMIN_ENTRY"] = "admin_" + _random_token(8)
    settings["SECRET_KEY"] = _random_token(32)
    for sub in ("data", "logs"):
        os.makedirs(os.path.join(data_dir, sub), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(settings, f, allow_unicode=True, sort_keys=False)
    return path


def _bootstrap(data_dir, webui_dir):
    os.environ["PAN123_DATA_DIR"] = data_dir
    if webui_dir:
        os.environ["PAN123_WEBUI_DIR"] = webui_dir

    import loadSettings

    loadSettings.DATA_DIR = os.path.abspath(data_dir)
    loadSettings.SETTINGS_PATH = _settings_path(data_dir)
    loadSettings.reload_settings()
    return loadSettings


def _setting(key, default):
    """读配置；还没 bootstrap 过时退回默认值，保证 status() 永远可用。"""
    try:
        import loadSettings

        value = loadSettings.loadSettings(key)
        return default if value is None else value
    except Exception:  # noqa: BLE001
        return default


def _purge_app_modules():
    """丢掉业务模块缓存，让下一次 import 按新配置重建 Flask 应用。

    loadSettings / getGlobalLogger 保留：前者已经 reload 过，后者重建会叠加日志 handler。
    """
    vfs = sys.modules.get("file_system")
    if vfs is not None and getattr(vfs, "_vfs", None) is not None:
        try:
            vfs._vfs.db.conn.close()
        except Exception:  # noqa: BLE001
            pass

    keep = {"loadSettings", "getGlobalLogger", "android_entry"}
    for name, module in list(sys.modules.items()):
        if name in keep:
            continue
        path = getattr(module, "__file__", None)
        if path and os.path.dirname(os.path.abspath(path)) == APP_DIR:
            del sys.modules[name]
    for name in [n for n in sys.modules if n.startswith("api.")]:
        del sys.modules[name]


def _info():
    port = _RUNTIME["port"] or int(_setting("PORT", 33333))
    host = _RUNTIME["host"] or str(_setting("BIND_HOST", "127.0.0.1"))
    lan_ip = _lan_ip()
    display_host = lan_ip if host not in ("127.0.0.1", "localhost", "::1") else "127.0.0.1"
    return {
        "running": _SERVER is not None,
        "host": host,
        "port": port,
        "lanIp": lan_ip,
        "localUrl": f"http://127.0.0.1:{port}/",
        "panelUrl": f"http://{display_host}:{port}/",
        "webdavUrl": f"http://{display_host}:{port}{_setting('WEBDAV_MOUNT_PATH', '/dav')}",
        "adminPath": "/" + str(_setting("ADMIN_ENTRY", "admin")),
        "dataDir": _data_dir(),
        "settingsPath": _settings_path(_data_dir()) if _data_dir() else "",
    }


def init(data_dir, webui_dir=""):
    """Kotlin 侧任何调用之前先跑这个：建好数据目录和默认配置。"""
    with _LOCK:
        try:
            _ensure_settings_file(data_dir)
            _bootstrap(data_dir, webui_dir)
            return _json(ok=True, **_info())
        except Exception as e:  # noqa: BLE001
            return _json(ok=False, error=f"{e.__class__.__name__}: {e}")


def start(data_dir, webui_dir=""):
    """启动服务（幂等）。返回 {ok, error?, ...urls}"""
    global _SERVER, _THREAD
    with _LOCK:
        if _SERVER is not None:
            return _json(ok=True, alreadyRunning=True, **_info())
        try:
            _ensure_settings_file(data_dir)
            _bootstrap(data_dir, webui_dir)
            _purge_app_modules()
            import server  # import 时完成 create_app 和默认密码守卫

            from waitress import create_server

            _RUNTIME["host"] = str(server.BIND_HOST)
            _RUNTIME["port"] = int(server.PORT)
            _SERVER = create_server(
                server.app,
                host=_RUNTIME["host"],
                port=_RUNTIME["port"],
                threads=8,
                ident="123pan-android",
            )
            _THREAD = threading.Thread(
                target=_SERVER.run, name="123pan-waitress", daemon=True
            )
            _THREAD.start()
            return _json(ok=True, **_info())
        except SystemExit as e:  # 默认密码守卫
            _SERVER = None
            return _json(ok=False, error=str(e))
        except Exception as e:  # noqa: BLE001
            _SERVER = None
            return _json(
                ok=False,
                error=f"{e.__class__.__name__}: {e}\n{traceback.format_exc(limit=6)}",
                **_info(),
            )


def stop():
    global _SERVER, _THREAD
    with _LOCK:
        if _SERVER is None:
            return _json(ok=True, **_info())
        try:
            _SERVER.close()
        except Exception:  # noqa: BLE001
            pass
        if _THREAD is not None:
            _THREAD.join(timeout=5)
        _SERVER = None
        _THREAD = None
        _RUNTIME.update({"host": "", "port": 0})
        return _json(ok=True, **_info())


def restart(data_dir, webui_dir=""):
    stop()
    return start(data_dir, webui_dir)


def status():
    return _json(ok=True, **_info())


def read_settings():
    try:
        import yaml

        path = _settings_path(_data_dir())
        with open(path, "r", encoding="utf-8") as f:
            stored = yaml.safe_load(f) or {}
        settings = dict(_DEFAULT_SETTINGS)
        settings.update({k: v for k, v in stored.items() if v is not None})
        return _json(ok=True, settings=settings, path=path)
    except Exception as e:  # noqa: BLE001
        return _json(ok=False, error=str(e), settings=dict(_DEFAULT_SETTINGS))


def write_settings(text):
    """写回 settings.yaml；调用方随后 restart() 让新配置生效。"""
    try:
        import yaml

        incoming = json.loads(text)
        settings = dict(_DEFAULT_SETTINGS)
        settings.update({k: v for k, v in incoming.items() if v is not None})

        try:
            settings["PORT"] = int(settings["PORT"])
        except (TypeError, ValueError):
            return _json(ok=False, error="端口必须是数字")
        if not 1 <= settings["PORT"] <= 65535:
            return _json(ok=False, error="端口范围 1-65535")

        settings["BIND_HOST"] = str(settings["BIND_HOST"]).strip()
        if settings["BIND_HOST"] not in ("127.0.0.1", "0.0.0.0"):
            return _json(ok=False, error="监听地址只能是 127.0.0.1（仅本机）或 0.0.0.0（局域网）")

        if settings["BIND_HOST"] != "127.0.0.1":
            weak = [k for k, v in _DEFAULT_SECRETS.items() if str(settings[k]) == v]
            if weak:
                return _json(ok=False, error="对局域网开放前必须改掉默认密码：" + "、".join(weak))

        settings["WEBDAV_USERNAME"] = str(settings["WEBDAV_USERNAME"]).strip()
        if not settings["WEBDAV_USERNAME"] or not str(settings["WEBDAV_PASSWORD"]).strip():
            return _json(ok=False, error="WebDAV 用户名和密码不能为空")

        if not str(settings["ADMIN_ENTRY"]).strip():
            settings["ADMIN_ENTRY"] = "admin_" + _random_token(8)
        if not str(settings["SECRET_KEY"]).strip():
            settings["SECRET_KEY"] = _random_token(32)
        settings["SPLIT_FOLDER"] = bool(settings["SPLIT_FOLDER"])
        settings["BAN_IP"] = bool(settings["BAN_IP"])

        path = _settings_path(_data_dir())
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(settings, f, allow_unicode=True, sort_keys=False)
        return _json(ok=True, path=path, settings=settings)
    except Exception as e:  # noqa: BLE001
        return _json(ok=False, error=f"{e.__class__.__name__}: {e}")


def download_database(data_dir=""):
    """拉作者维护的公共分享库并合并进本地库（可选，库很大，建议 WiFi 下做）。"""
    try:
        if data_dir:
            _ensure_settings_file(data_dir)
            _bootstrap(data_dir, "")

        from loadSettings import loadSettings

        from Pan123Database import Pan123Database

        db = Pan123Database(dbpath=loadSettings("DATABASE_PATH"))
        latest = db.downloadLatestDatabase()
        db.importDatabase(latest)
        db.close()
        return _json(ok=True, message="公共库导入完成")
    except Exception as e:  # noqa: BLE001
        return _json(ok=False, error=f"{e.__class__.__name__}: {e}")
