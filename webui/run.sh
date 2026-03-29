#!/bin/bash

# FedTracker WebUI Startup Script

echo "🌟 Starting FedTracker WebUI..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Change to webui directory
cd "$(dirname "$0")"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install Python 3.8+"
    exit 1
fi

# Install dependencies if needed
if [ ! -d "webui_env" ]; then
    echo "📦 Installing dependencies..."
    python3 -m pip install gradio matplotlib --quiet
fi

# Check if output directory exists
mkdir -p static/outputs

# Start the server
echo "🚀 Launching server on http://0.0.0.0:7860"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python3 app.py --port 7860 --host 0.0.0.0 "$@"