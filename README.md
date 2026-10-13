# 123Pan Unlimited 合并版（手机端 / Termux）

把上游两个项目合成**一个进程、一份配置、一个端口**：

- [123Pan-Unlimited-Share](https://github.com/realcwj/123Pan-Unlimited-Share) — Flask 网页面板（分享导入导出、搜索、公共库、管理后台、Telegram 爬虫）
- [123Pan-Unlimited-WebDAV](https://github.com/realcwj/123Pan-Unlimited-WebDAV) — FastAPI WebDAV（把公共库挂给 VidHub / Infuse / 网易爆米花等播放器）

两者本来就共用同一套核心（`Pan123.py` / `Pan123Database.py` / `utils.py` 逐字节相同），Share 负责产出数据库，WebDAV 消费同一份数据库。合并后：网页面板在 `/`，WebDAV 在 `/dav`，同端口。

> 上游为 GPLv3，本合并版同样 GPLv3。这些工具依赖 123 云盘的私有接口与“秒传”机制，**属于该网盘服务条款明确禁止的用法，账号有被风控/封禁的风险**；仅建议在你自己的账号、自己的设备上做技术验证，不要用于分发、牟利或任何非法用途。

---

## 目录结构

```
123pan-mobile/
├── app/                    # 合并后的 Python 代码（扁平布局，模块名互不冲突）
│   ├── server.py           # 新的统一入口：uvicorn + FastAPI(WebDAV) + a2wsgi(Flask)
│   ├── loadSettings.py     # 重写：全局缓存 + 绝对路径 + 不再弹 input()
│   ├── Pan123.py / Pan123Database.py / utils.py / getGlobalLogger.py / queueManager.py
│   ├── web.py + api/ + templates/ + static/          # 来自 Share
│   ├── file_system.py + models.py + auth.py + get_file_url.py + webdav_router.py  # 来自 WebDAV
│   └── telegramSpider.py + exportLinkToMutipleFolder.py   # CLI 工具
├── config/settings.example.yaml
├── requirements.txt
└── termux/
    ├── install.sh          # 一键安装（依赖 / 数据目录 / 配置 / 自检）
    └── pan.sh              # 安装为 `pan` 命令：start|stop|status|log|download-db|boot
```

运行时数据全部在 `~/.123pan/`（可用 `PAN123_DATA_DIR` 覆盖）：

```
~/.123pan/settings.yaml                 # 你真正要编辑的配置
~/.123pan/data/PAN123DATABASE.db        # 分享数据库（+ WAL 文件）
~/.123pan/logs/YYYY-MM-DD.log           # 应用日志（10MB × 5 轮转）
~/.123pan/logs/stdout.log               # 进程标准输出，崩溃栈在这里
~/.123pan/cache.json                    # 123 云盘 token 缓存（25 天）
~/.123pan/export/  ~/.123pan/share/     # CLI 工具的导出目录
```

---

## 在手机上安装（Termux，无需 Root）

1. 安装 **Termux**（用 GitHub / F-Droid 版，不要用 Play Store 版）。需要开机自启再装同签名的 **Termux:Boot**。
2. 在 Termux 里拉代码并安装：

```bash
pkg update -y && pkg install -y git
git clone https://github.com/YYNFFS/123pan-unlimited-mobile.git ~/123pan-mobile
cd ~/123pan-mobile && bash termux/install.sh
```

> 这是 **Private 私有仓库**，`git clone` 时 GitHub 会要凭据。最省事的做法：在 GitHub → Settings → Developer settings → Personal access tokens 生成一个只勾 `repo` 读权限的 fine-grained token，clone 时用户名填你的 GitHub 用户名、密码位置粘贴该 token。或者装 `gh`（Termux: `pkg install gh` → `gh auth login`）后用 `gh repo clone YYNFFS/123pan-unlimited-mobile ~/123pan-mobile`。

（不想用 git 也可以把整个目录压成 zip 传到手机，`unzip` 后同样跑 `termux/install.sh`。）

3. 填配置（**必须改掉全部默认密码，否则监听局域网时服务拒绝启动**）：

```bash
pan edit        # 等价于 nano ~/.123pan/settings.yaml
```

必填项：

| 键 | 说明 |
|---|---|
| `123PAN_USERNAME` / `123PAN_PASSWORD` | 你自己的 123 云盘账号，WebDAV 取直链要用 |
| `WEBDAV_USERNAME` / `WEBDAV_PASSWORD` | 播放器连接 WebDAV 用的账号密码，**改掉 `123456`** |
| `ADMIN_ENTRY` / `ADMIN_USERNAME` / `ADMIN_PASSWORD` | 网页管理后台入口与登录，全部要改 |
| `SECRET_KEY` | Flask session 密钥，改掉 |
| `BIND_HOST` | `0.0.0.0`=局域网可访问；`127.0.0.1`=仅本机 |
| `BAN_IP` | 手机在国内网络请保持 `False`，开了会把自己判定为“不受支持区域” |
| `SPLIT_FOLDER` | 只挂自己导出的库保持 `False`（根目录直接是分享名）；改用 `pan download-db` 拉作者的公共库时必须改回 `True` 并 `pan restart`，否则上万条目平铺会让播放器崩溃 |

4. 准备数据库（本项目默认按“只挂自己导出的库”配置）：
   - 自己攒库：浏览器打开面板，用“导出/导入”功能生成条目（默认走这条）
   - 或直接用作者发布的公共库：`pan download-db`，然后把 `SPLIT_FOLDER` 改成 `True` 并 `pan restart`

5. 启动：

```bash
pan start       # 后台常驻，自动 termux-wake-lock
pan status      # 状态 + /healthz 健康检查
pan log         # 最近日志
pan follow      # 实时跟踪
pan ip          # 打印给播放器用的地址
pan boot enable # 开机自启（需 Termux:Boot）
```

---

## 使用方式

- **网页面板**：`http://<手机IP>:33333/`，管理后台 `http://<手机IP>:33333/<ADMIN_ENTRY>/login`
- **WebDAV**：`http://<手机IP>:33333/dav`，用户名密码用 `WEBDAV_USERNAME/PASSWORD`
  - VidHub / Infuse / 网易爆米花：选 WebDAV，地址填上面这个，路径部分 `/dav` 不能漏
  - 只在本机播放：`http://127.0.0.1:33333/dav`
- 换了数据库文件后：`pan restart`（管理面板里的“更新数据库”会自动重建索引，不用重启）

## 常见问题

**手机息屏后播放器转圈 / 服务失联**
Android 会冻结后台并断 WiFi。`pan start` 已调用 `termux-wake-lock`，但仍需：设置 → 应用 → Termux → 电池 → 无限制；并在 Termux 里执行 `termux-wake-lock`。更稳妥的做法是让服务跑在常电设备上（盒子/旧手机/NAS），手机只当播放器。

**启动报“未找到配置文件”**
`~/.123pan/settings.yaml` 不存在，跑 `bash termux/install.sh` 或手动 `cp config/settings.example.yaml ~/.123pan/settings.yaml`。

**启动报“仍在使用默认密码”**
预期行为：`BIND_HOST` 不是 `127.0.0.1` 时不允许沿用出厂密码。

**播放时 502**
取直链失败。看 `pan log`：多为账号密码错、账号非会员无法读该资源、或云盘接口风控。设 `WEBDAV_FALLBACK_URL` 可让失败时跳占位视频而不是报错。

**首次打开 WebDAV 很慢**
内存索引是懒加载的（只有真正访问 `/dav` 才建），第一次 PROPFIND 会全库读入内存，之后走缓存。

**数据库锁 / 搜索无结果**
合并版已开 WAL + busy_timeout。若你用的 Python 的 sqlite 没编译 FTS5，全文搜索会退化（建表已做容错，不会阻止启动），换 Termux 官方 `pkg install python` 即可。

**Telegram 爬虫**
`python app/telegramSpider.py`，逐条确认需要交互终端；后台批量跑请加 `PAN123_AUTO_YES=1`。t.me 需要在能访问 Telegram 的网络下才通。

---

## 相对上游的改动清单

合并本身（不改变业务逻辑）：
- 新增 `app/server.py`：uvicorn 单进程同时提供 FastAPI(WebDAV, `/dav`) 与 Flask 面板（`a2wsgi.WSGIMiddleware` 挂到 `/`），不再需要 Gunicorn/Docker
- `loadSettings.py` 重写：按文件位置/环境变量定位配置，全进程缓存一次，路径统一落在数据目录，删除自动生成配置 + `input()` 阻塞
- 配置模板合并两侧全部键，`DATABASE_PATH` 只有一份（上游两个默认值不一致：`./PAN123DATABASE.db` vs `./assets/PAN123DATABASE.db`）
- `getGlobalLogger.py` 保留 Flask 版（WebDAV 版是空壳 stub），补上真正的轮转上限

手机端适配与稳定性修复：
- `Pan123Database` 开 `WAL + busy_timeout + synchronous=NORMAL`：两个服务同进程并发读写同一个库不再 `database is locked`；FTS5 建表失败降级而非崩溃
- `webdav_router` 的处理函数由 `async def` 改为同步 `def`：取直链是阻塞的 requests 调用，原来会**卡死整个事件循环**，同进程后还会连累网页面板；现在由 FastAPI 丢进线程池
- WebDAV 挂到 `/dav` 前缀，且懒构建虚拟文件系统（只用面板功能时不吃内存）
- `file_system.load_data_into_memory` 改为单次流式查询（新增 `Pan123Database.iterVisibleShares`），替掉分页读 + 每条一次 `getDataByHash` 的 N+1 查询
- `Pan123.py` / `utils.py` / `get_file_url.py` / 数据库下载全部补上 HTTP 超时（原代码所有云盘请求无 timeout，弱网会永久挂住线程）
- `get_file_url.py` 失败不再重定向到作者写死的占位视频，而是记日志 + 返回 502（可用 `WEBDAV_FALLBACK_URL` 恢复旧行为）；token 缓存加锁
- `auth.py` / `getGlobalLogger.py` / CLI 脚本：不再把密码打进日志，密码校验兼容空值
- 管理后台“更新数据库”成功后自动重建 WebDAV 内存索引
- 默认密码 + 监听 `0.0.0.0` 时拒绝启动

## 为什么没做成 Magisk 模块

你手机已 Root，但这个服务本身完全不需要 Root：要的是 Python 运行时、可写数据目录、能对外提供 HTTP，这些 Termux 都给了，而 Magisk 模块得自带 arm64 独立 Python、绕 SELinux、处理 `/data/adb` 下的存储权限，收益只有“比 Termux:Boot 更早启动”。如果确实要 Magisk 版（例如你要在 Termux 被杀的环境里跑，或想随 ROM 一起起来），说一声，我按 `service.sh + 内置 python 运行时` 再出一版。

## 开发自检

```bash
python -m compileall app          # 语法
python app/server.py              # 需要 ~/.123pan/settings.yaml
curl http://127.0.0.1:33333/healthz
```
