#!/bin/bash
# Auto-rebuild and serve documentation with live reload.
# Development mode:
# - Root path (/) is English with live reload
# - /en/ mirrors the English build
# - /zh-CN/ is rebuilt after each successful English build

echo "🚀 Starting ToolUniverse documentation with auto-reload..."
echo ""
echo "📝 Any changes to docs or src files will automatically rebuild English docs"
echo "🌍 Local multi-language paths:"
echo "   - /            English (live reload)"
echo "   - /en/         English mirror"
echo "   - /zh-CN/      Chinese rebuild after each change"
echo "🌐 Documentation will be available at: http://127.0.0.1:8000"
echo ""
echo "Press Ctrl+C to stop"
echo ""

cd "$(dirname "$0")"

if [ -x "../.venv/bin/sphinx-autobuild" ]; then
  SPHINX_AUTOBUILD="../.venv/bin/sphinx-autobuild"
elif command -v sphinx-autobuild >/dev/null 2>&1; then
  SPHINX_AUTOBUILD="$(command -v sphinx-autobuild)"
else
  echo "sphinx-autobuild not found. Install docs dependencies first."
  echo "Run: cd /Users/apple/learn/ToolUniverse && source .venv/bin/activate && pip install -e \".[docs]\" -r docs/requirements.txt"
  exit 1
fi

if [ -x "../.venv/bin/python" ]; then
  PYTHON_BIN="../.venv/bin/python"
else
  PYTHON_BIN="$(command -v python3)"
fi

"$SPHINX_AUTOBUILD" . _build/html \
  --host 127.0.0.1 \
  --port 8000 \
  --open-browser \
  --watch ../src \
  --post-build "$PYTHON_BIN post_build_multilang.py"
