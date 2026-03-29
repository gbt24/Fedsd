#!/bin/bash

echo "🚀 Starting FedTracker WebUI (Dark Theme)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd "$(dirname "$0")"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found"
    exit 1
fi

# Create output directory
mkdir -p static/outputs

# Start server
echo "🌐 Starting server on http://0.0.0.0:7860"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

python3 app.py --port 7860 --host 0.0.0.0 "$@"