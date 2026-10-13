#!/data/data/com.termux/files/usr/bin/bash
# pan —— 123Pan 合并版服务控制命令（由 install.sh 安装为 `pan`）
set -uo pipefail

REPO_DIR="${PAN123_REPO_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
# 通过 $PREFIX/bin/pan 运行时 dirname 是 bin，需要回退到仓库目录
if [ ! -f "$REPO_DIR/app/server.py" ]; then
    REPO_DIR="${PAN123_REPO_DIR:-$HOME/123pan-mobile}"
fi
APP_DIR="$REPO_DIR/app"
DATA_DIR="${PAN123_DATA_DIR:-$HOME/.123pan}"
SETTINGS="${PAN123_SETTINGS:-$DATA_DIR/settings.yaml}"
PIDFILE="$DATA_DIR/server.pid"
STDOUT_LOG="$DATA_DIR/logs/stdout.log"

port() {
    [ -f "$SETTINGS" ] && sed -n 's/^PORT:[[:space:]]*\([0-9]\+\).*/\1/p' "$SETTINGS" | head -1
}

is_running() {
    [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null
}

cmd_start() {
    if is_running; then
        echo "已在运行 (PID $(cat "$PIDFILE"))"
        return 0
    fi
    [ -f "$APP_DIR/server.py" ] || { echo "找不到 $APP_DIR/server.py，请设置 PAN123_REPO_DIR"; return 1; }
    [ -f "$SETTINGS" ] || { echo "找不到配置文件 $SETTINGS，先运行 install.sh"; return 1; }

    mkdir -p "$DATA_DIR/logs" "$DATA_DIR/data"
    # 保持 CPU/WiFi 唤醒，否则手机息屏后服务会被冻结
    command -v termux-wake-lock >/dev/null && termux-wake-lock

    nohup python "$APP_DIR/server.py" >>"$STDOUT_LOG" 2>&1 &
    echo $! >"$PIDFILE"
    sleep 3
    if is_running; then
        echo "已启动 (PID $(cat "$PIDFILE"))  端口 $(port)"
        cmd_ip
    else
        echo "启动失败，最后 30 行日志："
        tail -30 "$STDOUT_LOG" 2>/dev/null
        return 1
    fi
}

cmd_stop() {
    if ! is_running; then
        echo "未在运行"
        rm -f "$PIDFILE"
        return 0
    fi
    pid=$(cat "$PIDFILE")
    kill "$pid" 2>/dev/null
    for _ in 1 2 3 4 5 6 7 8 9 10; do
        kill -0 "$pid" 2>/dev/null || break
        sleep 1
    done
    kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null
    rm -f "$PIDFILE"
    echo "已停止"
}

cmd_status() {
    if is_running; then
        echo "运行中  PID $(cat "$PIDFILE")  端口 $(port)"
        if command -v curl >/dev/null; then
            curl -s --max-time 5 "http://127.0.0.1:$(port)/healthz" || echo "（/healthz 无响应）"
            echo
        fi
    else
        echo "未运行"
        [ -f "$PIDFILE" ] && echo "（残留 pidfile: $PIDFILE）"
    fi
}

cmd_log() {
    tail -n "${1:-60}" "$DATA_DIR"/logs/*.log 2>/dev/null || tail -n "${1:-60}" "$STDOUT_LOG"
}

cmd_follow() {
    tail -f "$STDOUT_LOG" "$DATA_DIR"/logs/*.log 2>/dev/null
}

cmd_ip() {
    ip=$(ip -4 addr show 2>/dev/null | awk '/inet (192\.168|10\.|172\.(1[6-9]|2[0-9]|3[01]))/{print $2}' | cut -d/ -f1 | head -1)
    [ -n "$ip" ] || ip="<手机的局域网IP，需在手机设置里查看>"
    echo "网页面板:  http://$ip:$(port)/"
    echo "WebDAV:    http://$ip:$(port)/dav   （播放器里填这个）"
}

cmd_download_db() {
    # 下载作者发布的公共数据库并合并进本地库
    python - "$APP_DIR" <<'PY'
import sys, os
sys.path.insert(0, sys.argv[1])
from Pan123Database import Pan123Database
from loadSettings import loadSettings
from getGlobalLogger import logger

db = Pan123Database(dbpath=loadSettings("DATABASE_PATH"))
path = db.downloadLatestDatabase()
logger.info(f"已下载到 {path}，开始合并（条目多时可能需要几分钟）...")
db.importDatabase(path)
db.close()
print("数据库更新完成。若 WebDAV 正在运行，用 `pan restart` 重建内存索引。")
PY
}

cmd_boot() {
    boot_dir="$HOME/.termux/boot"
    pan_bin="${PREFIX:-/data/data/com.termux/files/usr}/bin/pan"
    case "${1:-status}" in
        enable|on)
            mkdir -p "$boot_dir"
            cat >"$boot_dir/123pan.sh" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
# 由 \`pan boot enable\` 生成
termux-wake-lock
"$pan_bin" start
EOF
            chmod +x "$boot_dir/123pan.sh"
            echo "已写入 $boot_dir/123pan.sh"
            echo "前提：手机需安装 Termux:Boot 应用（与 Termux 同签名），并确保 Termux 未被电池优化杀掉。"
            ;;
        disable|off)
            rm -f "$boot_dir/123pan.sh"
            echo "已移除开机自启脚本"
            ;;
        *)
            [ -f "$boot_dir/123pan.sh" ] && echo "开机自启: 已启用" || echo "开机自启: 未启用"
            ;;
    esac
}

usage() {
    cat <<EOF
用法: pan <命令>

  start            后台启动服务（面板 + WebDAV 同端口）
  stop             停止
  restart          重启
  status           查看运行状态与健康检查
  log [行数]       打印最近日志（默认 60 行）
  follow           实时跟踪日志
  ip               显示局域网访问地址
  download-db      下载并合并作者发布的最新公共数据库
  boot <on|off>    开机自启（需 Termux:Boot）
  edit             编辑配置文件
EOF
}

case "${1:-}" in
    start) cmd_start ;;
    stop) cmd_stop ;;
    restart) cmd_stop; cmd_start ;;
    status) cmd_status ;;
    log) cmd_log "${2:-60}" ;;
    follow) cmd_follow ;;
    ip) cmd_ip ;;
    download-db) cmd_download_db ;;
    boot) cmd_boot "${2:-}" ;;
    enable) cmd_boot enable ;;
    disable) cmd_boot disable ;;
    edit) "${EDITOR:-nano}" "$SETTINGS" ;;
    ""|help|-h|--help) usage ;;
    *) echo "未知命令: $1"; usage; exit 1 ;;
esac
