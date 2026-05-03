#!/bin/bash
# Auto-rebuild and serve documentation with live reload

echo "🚀 Starting ToolUniverse documentation with auto-reload..."
echo ""
echo "📝 Any changes to .rst or .css files will automatically rebuild"
echo "🌐 Documentation will be available at: http://127.0.0.1:8000"
echo ""
echo "Press Ctrl+C to stop"
echo ""

cd "$(dirname "$0")"
uv run sphinx-autobuild . _build/html --port 8000 --open-browser
