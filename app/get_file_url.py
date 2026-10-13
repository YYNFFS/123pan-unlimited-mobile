import base64
import json
import os
import threading
import time

import requests

from Pan123 import Pan123
from loadSettings import loadSettings, data_path
from getGlobalLogger import logger

# token 缓存放在数据目录，重启后 25 天内免登录
CACHE_PATH = data_path("cache.json")
_CACHE_LOCK = threading.Lock()

# 失败时重定向到这个视频（原作者的占位素材），比直接 500 更容易让播放器给出提示
FALLBACK_URL = loadSettings("WEBDAV_FALLBACK_URL")


def _read_cache():
    with _CACHE_LOCK:
        if not os.path.exists(CACHE_PATH):
            return {"accessToken": "", "tokenCreateTime": "", "lastDeleteTime": ""}
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"cache.json 读取失败，将重新登录: {e}")
            return {"accessToken": "", "tokenCreateTime": "", "lastDeleteTime": ""}


def _write_cache(cache_data):
    with _CACHE_LOCK:
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=4, ensure_ascii=False)


def _timeout():
    return loadSettings("REQUEST_TIMEOUT_SECONDS") or 30


def _fail(reason: str) -> str:
    logger.error(f"WebDAV 取直链失败: {reason}")
    if FALLBACK_URL:
        return FALLBACK_URL
    raise RuntimeError(reason)


def get_file_url(name, etag, size) -> str:
    username = loadSettings("123PAN_USERNAME")
    password = loadSettings("123PAN_PASSWORD")
    if not username or not password:
        return _fail("settings.yaml 未配置 123PAN_USERNAME / 123PAN_PASSWORD")

    driver = Pan123()
    cache_data = _read_cache()

    # accessToken 30天有效, 这里按 25 天提前刷新
    if (
        cache_data.get("tokenCreateTime")
        and time.time() - cache_data.get("tokenCreateTime") < 25 * 24 * 60 * 60
        and cache_data.get("accessToken")
    ):
        driver.setAccessToken(cache_data.get("accessToken"))
    else:
        driver.doLogin(username=username, password=password)
        if driver.getAccessToken() is None:
            return _fail("123 云盘登录失败，请检查账号密码或是否被风控")
        cache_data["accessToken"] = driver.getAccessToken()
        cache_data["tokenCreateTime"] = int(time.time())
        _write_cache(cache_data)

    # 在云盘里维护一个缓存目录，秒传写入元数据后取直链，不占实际空间
    action_result = driver.createFolder(
        0, "__缓存目录_无视即可_24h自动清理__123Pan-Unlimited-WebDAV", True
    )
    if not action_result.get("isFinish"):
        return _fail(f"创建缓存目录失败: {action_result.get('message')}")
    cacheFolderInfo = action_result.get("message").get("Info")
    cacheFolderId = cacheFolderInfo.get("FileId")

    action_result = driver.uploadFile(
        etag=etag,
        fileName=name,
        parentFileId=cacheFolderId,
        size=size,
        raw_data=True,
    )
    if not action_result.get("isFinish"):
        return _fail(f"秒传提交失败: {action_result.get('message')}")
    file_data = action_result.get("message").get("Info")

    action_result = driver.downloadFile(
        etag=file_data.get("Etag"),
        fileId=file_data.get("FileId"),
        S3KeyFlag=file_data.get("S3KeyFlag"),
        type=file_data.get("Type"),
        fileName=file_data.get("FileName"),
        size=file_data.get("Size"),
    )
    if not action_result.get("isFinish"):
        return _fail(f"获取下载地址失败: {action_result.get('message')}")
    download_link = action_result.get("message")

    # 缓存目录每 24 小时彻底删除重建一次，避免文件堆积
    if not cache_data.get("lastDeleteTime"):
        cache_data["lastDeleteTime"] = int(time.time())
        _write_cache(cache_data)
    if time.time() - cache_data.get("lastDeleteTime") > 24 * 60 * 60:
        action_result = driver.deleteFile([cacheFolderInfo], True)
        if not action_result.get("isFinish"):
            logger.warning(f"清理缓存目录失败: {action_result.get('message')}")
        else:
            logger.info(f"彻底删除缓存文件夹 {cacheFolderInfo.get('FileName')} 成功")
            cache_data["lastDeleteTime"] = int(time.time())
            _write_cache(cache_data)

    real_url = download_link.split("params=")[-1].split("&")[0]
    real_url = base64.b64decode(real_url).decode("utf-8")

    headers = {"Referer": "https://www.123pan.com/"}
    try:
        response = requests.get(
            real_url, headers=headers, allow_redirects=False, timeout=_timeout()
        )
    except requests.RequestException as e:
        return _fail(f"探测最终直链时网络错误: {e}")

    if response.status_code == 302:
        final_url = response.headers.get("location")
    elif response.status_code < 300:
        try:
            final_url = response.json().get("data", {}).get("redirect_url")
        except (requests.exceptions.JSONDecodeError, AttributeError):
            return _fail("直链探测返回 2xx 但不是预期 JSON")
    else:
        return _fail(f"直链探测返回状态码 {response.status_code}")

    if not final_url:
        return _fail("未能解析出最终播放直链")

    logger.info(f"获取到 {name} 的真实 URL")
    return final_url


if __name__ == "__main__":
    name = "提灯映桃花 晚安时间到·楚河（CV：袁铭喆）微博@种草小呆萌.mp4"
    etag = "df5f8f335a1043be16e3e6e8f83c3072"
    size = 552721
    print(get_file_url(name=name, etag=etag, size=size))
