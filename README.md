# 123Pan Unlimited 合并版（安卓 APK / 手机常驻服务）

把上游两个项目合成**一个进程、一份配置、一个端口**：

- [123Pan-Unlimited-Share](https://github.com/realcwj/123Pan-Unlimited-Share) — Flask 网页面板（分享导入导出、搜索、公共库、管理后台、Telegram 爬虫）
- [123Pan-Unlimited-WebDAV](https://github.com/realcwj/123Pan-Unlimited-WebDAV) — WebDAV（把库挂给 VidHub / Infuse / 网易爆米花等播放器）

两者本来就共用同一套核心（`Pan123.py` / `Pan123Database.py` / `utils.py` 逐字节相同），Share 负责产出数据库，WebDAV 消费同一份数据库。合并后：网页面板在 `/`，WebDAV 在 `/dav`，同端口。

提供两种运行方式：

| | 方式一：APK（推荐） | 方式二：Termux 脚本 |
|---|---|---|
| 上手成本 | 装完打开即监听 | 要配 Termux 环境 |
| 界面 | 常驻通知 + App 内面板 + 设置页 | `pan start/status/log` 命令行 |
| 开机自启 | App 内开关 | 需装 Termux:Boot |
| Python | 由 Chaquopy 打进 APK，不依赖系统 | 用 Termux 的 python |

> 上游为 GPLv3，本合并版同样 GPLv3。这些工具依赖 123 云盘的私有接口与“秒传”机制，**属于该网盘服务条款明确禁止的用法，账号有被风控/封禁的风险**；仅建议在你自己的账号、自己的设备上做技术验证，不要用于分发、牟利或任何非法用途。

---

## 方式一：装 APK

APK 由本仓库的 GitHub Actions 构建（不需要你本地有 Android SDK）：

1. 打开仓库 → **Actions** → **Build Android APK** → 最近一次成功的 run → 下载 `123pan-android-apk` 里的 `app-debug.apk`
   （私有仓库要先登录 GitHub；命令行：`gh run download <run-id> -n 123pan-android-apk`）
2. 传到手机安装，允许“来自此来源的应用”。要求 Android 7.0+，arm64。
3. 打开 App：自动申请通知权限 → 自动开始监听 → 通知栏显示面板和 WebDAV 地址。
4. 进 **设置** 填 123 云盘账号、改掉 WebDAV / 管理后台密码，打开「允许局域网访问」，保存后服务自动重启。
5. 攒库：点 **打开网页面板** → 用“导出/导入”把分享链接导进本地数据库；或点 **下载公共分享库** 拉作者维护的公共库（很大，建议 WiFi，且要把设置里的“按哈希分桶”打开）。

App 里各按钮：

- **启动/停止服务** — 停止会真正释放端口，通知同时消失
- **打开网页面板** — 内嵌 WebView，走 `http://127.0.0.1:端口/`
- **复制地址** — 把本机/局域网/WebDAV/后台四个地址一次拷走
- **查看日志** — 直接看当天的应用日志尾部
- **开机后自动启动** — 依赖 `BOOT_COMPLETED`，国产 ROM 请在系统设置里给本 App 放行“自启动 + 后台无限制”

注意事项：

- CI 每次构建的 debug 签名都是新密钥，**升级 APK 前先卸载旧版**，否则会 `INSTALL_FAILED_UPDATE_INCOMPATIBLE`。数据在应用私有目录，卸载即清空，先导出数据库备份。
- 数据位置：`/data/data/com.pan123.unlimited/files/pan/`（`settings.yaml`、`data/PAN123DATABASE.db`、`logs/`）。已 Root 的机器可以直接 `cp` 出来改。
- 手机息屏/省电策略仍可能杀后台：设置 → 应用 → 123Pan → 电池 → 无限制。

## 方式二：Termux 脚本

1. 安装 **Termux**（用 GitHub / F-Droid 版，不要用 Play Store 版）。需要开机自启再装同签名的 **Termux:Boot**。
2. 拉代码并安装：

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

4. 启动：

```bash
pan start       # 后台常驻，自动 termux-wake-lock
pan status      # 状态 + /healthz 健康检查
pan log         # 最近日志
pan follow      # 实时跟踪
pan ip          # 打印给播放器用的地址
pan boot enable # 开机自启（需 Termux:Boot）
```

---

## 配置项

APK 的设置页只暴露了常用几项，其余要改 `settings.yaml`（Termux 下直接改，APK 下需 Root 或用面板的管理后台）。

| 键 | 说明 |
|---|---|
| `123PAN_USERNAME` / `123PAN_PASSWORD` | 你自己的 123 云盘账号，WebDAV 取直链要用 |
| `WEBDAV_USERNAME` / `WEBDAV_PASSWORD` | 播放器连接 WebDAV 用的账号密码，**改掉 `123456`** |
| `ADMIN_ENTRY` / `ADMIN_USERNAME` / `ADMIN_PASSWORD` | 网页管理后台入口与登录，全部要改 |
| `SECRET_KEY` | Flask session 密钥，改掉 |
| `BIND_HOST` | `0.0.0.0`=局域网可访问；`127.0.0.1`=仅本机 |
| `PORT` | 监听端口，APK 默认 33333 |
| `BAN_IP` | 手机在国内网络请保持 `False`，开了会把自己判定为“不受支持区域” |
| `SPLIT_FOLDER` | 只挂自己导出的库保持 `False`（根目录直接是分享名）；改用公共库时必须改回 `True` 并重启，否则上万条目平铺会让播放器崩溃 |

## 使用方式

- **网页面板**：`http://<手机IP>:33333/`，管理后台 `http://<手机IP>:33333/<ADMIN_ENTRY>/login`
- **WebDAV**：`http://<手机IP>:33333/dav`，用户名密码用 `WEBDAV_USERNAME/PASSWORD`
  - VidHub / Infuse / 网易爆米花：选 WebDAV，地址填上面这个，路径部分 `/dav` 不能漏
  - 只在本机播放：`http://127.0.0.1:33333/dav`
- 换了数据库文件后：Termux 用 `pan restart`（管理面板里的“更新数据库”会自动重建索引，不用重启）；APK 保存设置时自动重启服务

## 目录结构

```
123pan-mobile/
├── app/                    # 合并后的 Python 代码（扁平布局，模块名互不冲突）
│   ├── server.py           # 统一入口：Flask 面板 + WebDAV 蓝图 + waitress
│   ├── android_entry.py    # APK 唯一入口：start/stop/restart/read_settings/write_settings
│   ├── loadSettings.py     # 全局缓存 + 绝对路径 + 不再弹 input()
│   ├── Pan123.py / Pan123Database.py / utils.py / getGlobalLogger.py / queueManager.py
│   ├── web.py + api/ + templates/ + static/          # 来自 Share
│   ├── file_system.py + models.py + auth.py + get_file_url.py + webdav.py   # 来自 WebDAV
│   └── telegramSpider.py + exportLinkToMutipleFolder.py   # CLI 工具
├── android/                # APK 工程（Kotlin + Chaquopy，无第三方依赖）
├── config/settings.example.yaml
├── requirements.txt        # 全部纯 Python 包
├── termux/                 # install.sh + pan 控制命令
└── .github/workflows/android.yml
```

Termux/桌面数据在 `~/.123pan/`（`PAN123_DATA_DIR` 可覆盖），APK 数据在应用私有目录：

```
settings.yaml                    # 你真正要编辑的配置
data/PAN123DATABASE.db           # 分享数据库（+ WAL 文件）
logs/YYYY-MM-DD.log              # 应用日志（10MB × 5 轮转）
logs/stdout.log                  # 进程标准输出（仅 Termux），崩溃栈在这里
cache.json                       # 123 云盘 token 缓存（25 天）
export/  share/                  # CLI 工具的导出目录
```

## 常见问题

**手机息屏后播放器转圈 / 服务失联**
Android 会冻结后台并断 WiFi。APK 用了前台服务，仍需在 设置 → 应用 → 123Pan → 电池 → 无限制；Termux 版额外执行 `termux-wake-lock`。更稳妥的做法是让服务跑在常电设备上（盒子/旧手机/NAS），手机只当播放器。

**启动报“未找到配置文件”**
Termux 下跑 `bash termux/install.sh` 或 `cp config/settings.example.yaml ~/.123pan/settings.yaml`；APK 首次启动会自动生成。

**启动报“仍在使用默认密码”**
预期行为：`BIND_HOST` 不是 `127.0.0.1` 时不允许沿用出厂密码。APK 的设置页同样会拒绝保存。

**播放时 502**
取直链失败。看日志：多为账号密码错、账号非会员无法读该资源、或云盘接口风控。设 `WEBDAV_FALLBACK_URL` 可让失败时跳占位视频而不是报错。

**首次打开 WebDAV 很慢**
内存索引是懒加载的（只有真正访问 `/dav` 才建），第一次 PROPFIND 会全库读入内存，之后走缓存。

**数据库锁 / 搜索无结果**
合并版已开 WAL + busy_timeout。若所用 Python 的 sqlite 没编译 FTS5，全文搜索会退化（建表已做容错，不会阻止启动）。

**Telegram 爬虫**
`python app/telegramSpider.py`，逐条确认需要交互终端；后台批量跑请加 `PAN123_AUTO_YES=1`。t.me 需要在能访问 Telegram 的网络下才通。APK 里没有爬虫入口，需要它在 Termux/桌面跑。

---

## 相对上游的改动清单

合并本身（不改变业务逻辑）：
- 新增 `app/server.py`：单进程单端口同时提供网页面板（`/`）与 WebDAV（`/dav`），不再需要 Gunicorn/Docker
- `loadSettings.py` 重写：按文件位置/环境变量定位配置，全进程缓存一次，路径统一落在数据目录，删除自动生成配置 + `input()` 阻塞
- 配置模板合并两侧全部键，`DATABASE_PATH` 只有一份（上游两个默认值不一致：`./PAN123DATABASE.db` vs `./assets/PAN123DATABASE.db`）
- `getGlobalLogger.py` 保留 Flask 版（WebDAV 版是空壳 stub），补上真正的轮转上限

手机端适配与稳定性修复：
- `Pan123Database` 开 `WAL + busy_timeout + synchronous=NORMAL`：两个服务同进程并发读写同一个库不再 `database is locked`；FTS5 建表失败降级而非崩溃
- WebDAV 处理函数是同步的：取直链是阻塞的 requests 调用，原来放在事件循环里会**卡死整个服务**，同进程后还会连累网页面板
- WebDAV 挂到 `/dav` 前缀，且懒构建虚拟文件系统（只用面板功能时不吃内存）
- `file_system.load_data_into_memory` 改为单次流式查询（新增 `Pan123Database.iterVisibleShares`），替掉分页读 + 每条一次 `getDataByHash` 的 N+1 查询
- `Pan123.py` / `utils.py` / `get_file_url.py` / 数据库下载全部补上 HTTP 超时（原代码所有云盘请求无 timeout，弱网会永久挂住线程）
- `get_file_url.py` 失败不再重定向到作者写死的占位视频，而是记日志 + 返回 502（可用 `WEBDAV_FALLBACK_URL` 恢复旧行为）；token 缓存加锁
- `auth.py` / `getGlobalLogger.py` / CLI 脚本：不再把密码打进日志，密码校验兼容空值
- 管理后台“更新数据库”成功后自动重建 WebDAV 内存索引
- 默认密码 + 监听 `0.0.0.0` 时拒绝启动

APK 化：
- 依赖全部换成纯 Python 包：`fastapi + uvicorn + a2wsgi` → `Flask 蓝图 + waitress`。原因是 Chaquopy 只能装纯 Python 包或它自己预编译过的 wheel，而 FastAPI 依赖的 `pydantic-core` 是 Rust 扩展
- `android_entry.py`：进程内起 waitress（线程），提供 start/stop/restart/status/read_settings/write_settings/download_database，全部 JSON 出入参
- 改配置后由 `_purge_app_modules()` 丢掉业务模块缓存重建 Flask 应用，无需杀进程
- Flask 的 `templates/`、`static/` 不是 `.py`，Chaquopy 不打包 → 构建时复制成 assets，首次运行解压到应用目录，用 `PAN123_WEBUI_DIR` 告诉 `web.py` 去哪找
- 只打 `arm64-v8a`，APK 体积主要花在 CPython 运行时上

## 为什么不是 Magisk 模块

这个服务不需要 Root：要的是 Python 运行时、可写数据目录、能对外提供 HTTP，APK 里的 Chaquopy 已经把 CPython 打进进程。Magisk 模块得自带独立 Python、绕 SELinux、处理 `/data/adb` 下的存储权限，收益只有“比开机广播更早启动”。确实要 Magisk 版的话说一声，我按 `service.sh + 内置 python 运行时` 再出一版。

## 开发自检

```bash
python -m compileall app
python app/server.py                     # 需要 ~/.123pan/settings.yaml
curl http://127.0.0.1:33333/healthz
```
