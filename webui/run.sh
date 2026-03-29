#!/bin/bash
# FedTracker WebUI 启动脚本

echo "================================"
echo "  FedTracker WebUI 启动器"
echo "================================"
echo ""

# 显示帮助
show_help() {
    echo "使用方法:"
    echo "  ./run.sh              # 本地启动 (localhost:7860)"
    echo "  ./run.sh --share      # 启用公网分享"
    echo "  ./run.sh --auth admin:123456  # 设置密码保护"
    echo "  ./run.sh --share --auth admin:123456  # 公网分享+密码"
    echo ""
    echo "参数:"
    echo "  --share              生成公网访问链接 (Gradio隧道)"
    echo "  --auth 用户名:密码    设置登录验证"
    echo "  --port 端口号         自定义本地端口 (默认7860)"
    echo ""
}

# 解析参数
SHARE_FLAG=""
AUTH_FLAG=""
PORT_FLAG=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --share)
            SHARE_FLAG="--share"
            shift
            ;;
        --auth)
            AUTH_FLAG="--auth $2"
            shift 2
            ;;
        --port)
            PORT_FLAG="--port $2"
            shift 2
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            echo "未知参数: $1"
            show_help
            exit 1
            ;;
    esac
done

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 Python3"
    exit 1
fi

# 进入webui目录
cd "$(dirname "$0")"

# 检查并安装依赖
echo "检查依赖..."
if ! python3 -c "import gradio" 2>/dev/null; then
    echo "安装依赖..."
    pip install -r requirements.txt
fi

echo ""
echo "启动 WebUI..."

# 构建命令
CMD="python3 app.py $PORT_FLAG $SHARE_FLAG $AUTH_FLAG"
echo "执行: $CMD"
echo ""

# 启动应用
exec $CMD
