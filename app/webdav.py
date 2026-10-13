# -*- coding: utf-8 -*-

import datetime
import threading
from urllib.parse import quote
from xml.sax.saxutils import escape

from flask import Blueprint, Response, redirect, request

from auth import require_basic_auth
from file_system import get_vfs
from getGlobalLogger import logger
from get_file_url import get_file_url
from models import TYPE_DIRECTORY, TYPE_FILE

# 只读 WebDAV：PROPFIND 列目录 + GET 取直链后 307 跳转到 CDN。
# 挂成 Flask Blueprint 而不是独立服务，这样面板和 WebDAV 共用一个端口、
# 一个进程，Android/Termux 上只需要起一个 WSGI server。
webdav_bp = Blueprint("webdav", __name__)

_METHODS = ["GET", "HEAD", "OPTIONS", "PROPFIND"]

# 同一进程内 WebDAV 跑在线程池里；根目录列表会原地重建 root.children，
# 并发时可能让另一个客户端拿到半截列表，所以路径解析加一把锁。
_VFS_LOCK = threading.RLock()

# WebDAV 响应需要的XML命名空间
XML_NS = 'xmlns:D="DAV:"'


def _build_propfind_response_xml(node, href: str) -> str:
    """为单个节点生成 PROPFIND 响应中的 <D:response> XML 片段。"""
    # 确保目录的 href 总是以斜杠结尾
    final_href = href
    if node.type == TYPE_DIRECTORY and not final_href.endswith("/"):
        final_href += "/"

    if node.type == TYPE_DIRECTORY:
        resourcetype = "<D:resourcetype><D:collection/></D:resourcetype>"
    else:
        resourcetype = "<D:resourcetype/>"

    # 文件的 ETag (对于目录可以为空)
    etag_xml = f'<D:getetag>"{node.etag}"</D:getetag>' if node.etag else "<D:getetag/>"

    # 统一使用一个固定的时间戳，因为我们的文件系统是虚拟的且只读
    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 用 escape() 转义文件名，防止非法字符破坏 XML 结构
    display_name = escape(node.name)

    return f"""
    <D:response>
        <D:href>{final_href}</D:href>
        <D:propstat>
            <D:prop>
                <D:displayname>{display_name}</D:displayname>
                {resourcetype}
                <D:getcontentlength>{node.size}</D:getcontentlength>
                <D:getlastmodified>{now_iso}</D:getlastmodified>
                {etag_xml}
            </D:prop>
            <D:status>HTTP/1.1 200 OK</D:status>
        </D:propstat>
    </D:response>
    """


def _text(content: str, status: int, headers: dict = None) -> Response:
    return Response(content, status=status, headers=headers, mimetype="text/plain")


@webdav_bp.route("/", methods=_METHODS)
@webdav_bp.route("/<path:subpath>", methods=_METHODS)
@require_basic_auth
def handle_webdav_request(subpath: str = ""):
    """处理 WebDAV 请求的统一入口点。

    - OPTIONS: 返回服务器支持的方法
    - PROPFIND: 返回目录列表或文件属性
    - GET/HEAD: 对文件请求取直链并 307 跳转
    """
    client_ip = request.remote_addr
    method = request.method
    logger.debug(f"WebDAV 请求: 方法={method}, 路径='/{subpath}', 来源={client_ip}")

    if method == "OPTIONS":
        return _text(
            "",
            200,
            {
                "Allow": "OPTIONS, GET, HEAD, PROPFIND",
                "DAV": "1",
                "MS-Author-Via": "DAV",
            },
        )

    with _VFS_LOCK:
        node = get_vfs().get_node_by_path(subpath)
    if node is None:
        return _text("资源未找到", 404)

    if method in ("GET", "HEAD"):
        if node.type == TYPE_FILE:
            logger.info(f"WebDAV GET 文件: {node.name}")
            try:
                real_url = get_file_url(node.name, node.etag, node.size)
            except Exception as e:
                logger.error(f"获取直链异常: {e}", exc_info=True)
                return _text(f"获取云盘直链失败: {e}", 502)
            return redirect(real_url, code=307)
        return _text("不支持GET目录", 405)

    if method == "PROPFIND":
        depth = request.headers.get("Depth", "1")
        # 用 request.path 而不是 subpath，保证 href 带上 /dav 挂载前缀
        request_href = request.path

        responses_xml = _build_propfind_response_xml(node, request_href)

        if depth == "1" and node.type == TYPE_DIRECTORY:
            parent_href = request_href if request_href.endswith("/") else request_href + "/"
            for child in node.children:
                responses_xml += _build_propfind_response_xml(
                    child, f"{parent_href}{quote(child.name)}"
                )

        full_xml = (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            f"<D:multistatus {XML_NS}>\n{responses_xml}\n</D:multistatus>"
        )
        return Response(
            full_xml, status=207, mimetype="application/xml; charset=utf-8"
        )

    return _text("方法不允许", 405)
