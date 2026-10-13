#!/data/data/com.termux/files/usr/bin/bash
# 123Pan Unlimited 合并版 —— Termux 一键安装
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="${PAN123_DATA_DIR:-$HOME/.123pan}"
SETTINGS="$DATA_DIR/settings.yaml"
PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"

echo "== 123Pan 合并版安装 =="
echo "代码目录: $REPO_DIR"
echo "数据目录: $DATA_DIR"

if [ ! -d "$PREFIX" ]; then
    echo "未检测到 Termux 环境。请在 Termux 里运行本脚本，而不是在电脑或其他 shell 里。" >&2
    exit 1
fi

echo
echo "[1/5] 安装系统依赖 (python / git / curl)..."
pkg update -y
pkg install -y python git curl

echo
echo "[2/5] 安装 Python 依赖..."
# 不要 pip install --upgrade pip：Termux 的 python-pip 由包管理器托管，
# 自升级会报 "Installing pip is forbidden, this will break the python-pip package"
pip install -r "$REPO_DIR/requirements.txt"

echo
echo "[3/5] 准备数据目录与配置文件..."
mkdir -p "$DATA_DIR/data" "$DATA_DIR/logs" "$DATA_DIR/export" "$DATA_DIR/share"
if [ ! -f "$SETTINGS" ]; then
    cp "$REPO_DIR/config/settings.example.yaml" "$SETTINGS"
    echo "已生成配置文件: $SETTINGS  ← 必须编辑它填入你的 123 云盘账号"
else
    echo "配置文件已存在，保留不动: $SETTINGS"
fi

echo
echo "[4/5] 安装 pan 命令到 \$PREFIX/bin ..."
# 把仓库绝对路径写进安装后的脚本，这样从任意目录运行 pan 都能找到代码
sed "s|^REPO_DIR=.*|REPO_DIR=\"$REPO_DIR\"|" "$REPO_DIR/termux/pan.sh" > "$PREFIX/bin/pan"
chmod +x "$PREFIX/bin/pan"
echo "已安装: pan start / pan stop / pan status / pan log"

echo
echo "[5/5] 自检（导入所有模块，验证配置与依赖）..."
if python - "$REPO_DIR" <<'PY'
import sys, os
sys.path.insert(0, os.path.join(sys.argv[1], "app"))
import server  # noqa: F401
print("自检通过：Flask 面板 + WebDAV 路由均已加载。")
PY
then
    :
else
    echo "自检未通过。若提示“仍在使用默认密码”，属于预期行为——请先编辑 $SETTINGS 改掉密码再启动。"
    echo "若提示 ModuleNotFoundError，请把上面的报错整段贴出来排查。"
fi

cat <<EOF

安装完成。接下来：

  1) 编辑配置（123 云盘账号 + 改掉所有默认密码）：
       nano $SETTINGS
  2) 首次启动：
       pan start
  3) 查看状态 / 日志：
       pan status
       pan log

想开机自动启动，请安装 Termux:Boot 插件（APK），然后运行：
       pan boot enable

EOF
