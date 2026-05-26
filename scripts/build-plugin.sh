#!/usr/bin/env bash
set -euo pipefail

# Build the ToolUniverse Claude Code plugin
# Assembles: manifest + MCP config + skills + commands + agents

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLUGIN_SRC="$REPO_ROOT/plugin"
DIST_DIR="$REPO_ROOT/dist/tooluniverse-plugin"

echo "Building ToolUniverse Claude Code plugin..."

# Clean previous build
rm -rf "$DIST_DIR"
mkdir -p "$DIST_DIR"

# 1. Copy plugin manifest (plugin.json only — marketplace.json is for
# local-dev marketplace at plugin source; it should NOT ship inside the
# distributed plugin. Per official guidance, .claude-plugin/ at a plugin
# root holds only plugin.json.)
mkdir -p "$DIST_DIR/.claude-plugin"
cp "$PLUGIN_SRC/.claude-plugin/plugin.json" "$DIST_DIR/.claude-plugin/"
echo "  [+] Plugin manifest (plugin.json only)"

# 2. Copy MCP config
cp "$PLUGIN_SRC/.mcp.json" "$DIST_DIR/"
echo "  [+] MCP server config"

# 3. Copy settings
cp "$PLUGIN_SRC/settings.json" "$DIST_DIR/"
echo "  [+] Default settings"

# 4. Copy commands
cp -r "$PLUGIN_SRC/commands" "$DIST_DIR/"
echo "  [+] Slash commands"

# 4b. Copy helper scripts + bundle the generated API key catalog next to them.
# Use rsync to exclude __pycache__ / *.pyc so stray local artifacts don't ship.
rsync -a --exclude='__pycache__' --exclude='*.pyc' \
    "$PLUGIN_SRC/scripts/" "$DIST_DIR/scripts/"
cp "$REPO_ROOT/src/tooluniverse/data/api_keys_catalog.json" "$DIST_DIR/scripts/"
echo "  [+] Setup scripts + API key catalog"

# 5. Copy agents
cp -r "$PLUGIN_SRC/agents" "$DIST_DIR/"
echo "  [+] Research agent"

# 6. Copy hooks (SessionStart: clean up global skills)
if [ -d "$PLUGIN_SRC/hooks" ]; then
    cp -r "$PLUGIN_SRC/hooks" "$DIST_DIR/"
    echo "  [+] Hooks (SessionStart cleanup)"
fi

# 7. Copy README, CHANGELOG, and LICENSE
cp "$PLUGIN_SRC/README.md" "$DIST_DIR/"
if [ -f "$PLUGIN_SRC/CHANGELOG.md" ]; then
    cp "$PLUGIN_SRC/CHANGELOG.md" "$DIST_DIR/"
fi
# Apache-2.0 compliance: ship the LICENSE file with the distributed plugin.
# Source from the repo root since the plugin inherits the parent license.
if [ -f "$REPO_ROOT/LICENSE" ]; then
    cp "$REPO_ROOT/LICENSE" "$DIST_DIR/"
fi
echo "  [+] README + CHANGELOG + LICENSE"

# 7. Copy ALL tooluniverse skills
# The router is the only auto-matchable skill (visible description).
# All sub-skills have disable-model-invocation: true — their descriptions
# don't appear in context, so having 114 skills doesn't affect routing.
# They're available when the router dispatches via Skill('name').
#
# Exclude development artifacts that should NOT ship:
#   test_*.py / *_test.py — internal skill tests (some reference internal
#                           benchmark names that would leak to end users)
#   __pycache__/, *.pyc, .pytest_cache/ — Python build/cache artifacts
#   .DS_Store — macOS folder metadata
mkdir -p "$DIST_DIR/skills"
skill_count=0
for skill_dir in "$REPO_ROOT/skills"/*/; do
    dir_name=$(basename "$skill_dir")
    if [ -f "$skill_dir/SKILL.md" ] && [[ "$dir_name" == tooluniverse* ]]; then
        rsync -a \
            --exclude='test_*.py' \
            --exclude='*_test.py' \
            --exclude='__pycache__/' \
            --exclude='*.pyc' \
            --exclude='.pytest_cache/' \
            --exclude='.coverage' \
            --exclude='.coverage.*' \
            --exclude='coverage.xml' \
            --exclude='htmlcov/' \
            --exclude='.mypy_cache/' \
            --exclude='.ruff_cache/' \
            --exclude='.DS_Store' \
            "$skill_dir" "$DIST_DIR/skills/$dir_name/"
        skill_count=$((skill_count + 1))
    fi
done
echo "  [+] $skill_count skills (1 router + $((skill_count - 1)) sub-skills with disable-model-invocation)"

# 8. Summary
total_files=$(find "$DIST_DIR" -type f | wc -l | tr -d ' ')
total_size=$(du -sh "$DIST_DIR" | cut -f1)

echo ""
echo "Plugin built successfully!"
echo "  Location: $DIST_DIR"
echo "  Files: $total_files"
echo "  Size: $total_size"
echo ""
echo "Install:"
echo "  claude --plugin-dir $DIST_DIR"
echo ""
echo "Or test with:"
echo "  ls $DIST_DIR/.claude-plugin/plugin.json"
echo "  ls $DIST_DIR/skills/ | head -10"
