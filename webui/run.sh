#!/bin/bash
# FedTracker WebUI 启动脚本

echo "================================"
echo "  FedTracker WebUI 启动器"
echo "================================"
echo ""

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
echo "访问地址: http://localhost:7860"
echo ""

# 启动应用
python3 app.py