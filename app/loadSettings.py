import os
import yaml

# 合并版配置层：
# - 配置文件与数据目录不再依赖当前工作目录，可被 Termux 后台服务、CLI 脚本共用
# - 全进程只解析一次 settings.yaml（原实现每个模块 import 时都读盘）
# - 绝不弹 input()，缺配置直接抛异常，避免常驻服务被卡死

APP_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(APP_DIR)

DATA_DIR = os.path.abspath(
    os.environ.get("PAN123_DATA_DIR") or os.path.join(os.path.expanduser("~"), ".123pan")
)
SETTINGS_PATH = os.path.abspath(
    os.environ.get("PAN123_SETTINGS") or os.path.join(DATA_DIR, "settings.yaml")
)
SETTINGS_EXAMPLE_PATH = os.path.abspath(
    os.environ.get("PAN123_SETTINGS_EXAMPLE")
    or os.path.join(_PROJECT_DIR, "config", "settings.example.yaml")
)

# 只有这些键是磁盘路径，相对值一律落到 DATA_DIR 下
_PATH_KEYS = ("DATABASE_PATH", "LOG_DIR")

_DEFAULTS = {
    "BIND_HOST": "0.0.0.0",
    "PORT": 33333,
    "WEBDAV_MOUNT_PATH": "/dav",
    "DATABASE_PATH": "data/PAN123DATABASE.db",
    "LOG_DIR": "logs",
    "TASK_QUEUE_TIMEOUT_SECONDS": 600,
    "LOGGING_LEVEL": "INFO",
    "BAN_IP": False,
    "SPLIT_FOLDER": True,
    "REQUEST_TIMEOUT_SECONDS": 30,
}

_cache = None


def _load():
    global _cache
    if _cache is not None:
        return _cache

    if not os.path.exists(SETTINGS_PATH):
        raise FileNotFoundError(
            f"未找到配置文件: {SETTINGS_PATH}\n"
            f"请把模板复制过去再填参数:\n"
            f"  mkdir -p {DATA_DIR} && cp {SETTINGS_EXAMPLE_PATH} {SETTINGS_PATH}\n"
            f"（运行 termux/install.sh 会自动完成这一步）"
        )

    with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    merged = dict(_DEFAULTS)
    merged.update({k: v for k, v in data.items() if v is not None})

    for key in _PATH_KEYS:
        merged[key] = resolve_path(merged[key])

    if not os.path.isdir(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)

    _cache = merged
    return _cache


def resolve_path(value):
    """把配置里的相对路径解析为 DATA_DIR 下的绝对路径。"""
    if value is None:
        return None
    value = str(value).strip().strip('"').strip("'")
    if os.path.isabs(value):
        return os.path.normpath(value)
    if value.startswith("./"):
        value = value[2:]
    return os.path.normpath(os.path.join(DATA_DIR, value))


def data_path(*parts):
    path = os.path.join(DATA_DIR, *parts)
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)
    return path


def loadSettings(keyword, default=None):
    value = _load().get(keyword, default)
    if keyword in _PATH_KEYS and value is not None:
        return resolve_path(value)
    return value


def reload_settings():
    """配置热重载（改完 settings.yaml 后由 pan reload / 管理面板调用）。"""
    global _cache
    _cache = None
    return _load()
