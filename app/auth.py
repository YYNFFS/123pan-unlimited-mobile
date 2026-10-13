# -*- coding: utf-8 -*-

import base64
import secrets
from functools import wraps

from flask import request, Response

from loadSettings import loadSettings
from getGlobalLogger import logger

# WebDAV 用户名/密码在服务启动时读取一次；改密码后重启服务生效
CORRECT_USERNAME = str(loadSettings("WEBDAV_USERNAME"))
CORRECT_PASSWORD = str(loadSettings("WEBDAV_PASSWORD"))

_UNAUTHORIZED = Response(
    "需要 WebDAV 认证",
    status=401,
    headers={"WWW-Authenticate": 'Basic realm="123Pan", charset="UTF-8"'},
)


def _parse_basic(header: str):
    """从 Authorization 头解出 (username, password)，格式不对返回 None。"""
    if not header or not header.lower().startswith("basic "):
        return None
    token = header.split(None, 1)[1].strip()
    try:
        # 部分客户端会省略 base64 填充，这里补齐再解
        decoded = base64.b64decode(token + "=" * (-len(token) % 4)).decode("utf-8")
    except Exception:
        return None
    if ":" not in decoded:
        return None
    username, password = decoded.split(":", 1)
    return username, password


def require_basic_auth(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        credentials = _parse_basic(request.headers.get("Authorization", ""))
        if credentials is None or not (
            secrets.compare_digest(credentials[0].encode(), CORRECT_USERNAME.encode())
            and secrets.compare_digest(credentials[1].encode(), CORRECT_PASSWORD.encode())
        ):
            return _UNAUTHORIZED
        logger.debug(f"用户 '{credentials[0]}' WebDAV 认证成功。")
        return func(*args, **kwargs)

    return wrapper
