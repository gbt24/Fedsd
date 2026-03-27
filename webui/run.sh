#!/bin/bash
# -*- coding: UTF-8 -*-
# FedTracker WebUI启动脚本

set -e

# 切换到项目根目录 (Fedsd/)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "========================================"
echo "FedTracker WebUI Launcher"
echo "========================================"
echo "Project root: $PROJECT_ROOT"

# 检查Python环境
if ! command -v python &> /dev/null; then
    echo "Error: Python not found"
    exit 1
fi

# 创建输出目录
mkdir -p webui/static/outputs

# 检查依赖
echo "Checking dependencies..."
pip install -q gradio matplotlib 2>/dev/null || pip install gradio matplotlib

# 可选参数
PORT=${PORT:-7860}
HOST=${HOST:-0.0.0.0}
SHARE_FLAG=""
DEBUG_FLAG=""

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --share)
            SHARE_FLAG="--share"
            shift
            ;;
        --debug)
            DEBUG_FLAG="--debug"
            shift
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --host)
            HOST="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--share] [--debug] [--port PORT] [--host HOST]"
            exit 1
            ;;
    esac
done

echo "Starting server..."
echo "  Host: $HOST"
echo "  Port: $PORT"
echo "========================================"

python webui/app.py --host "$HOST" --port "$PORT" $SHARE_FLAG $DEBUG_FLAG