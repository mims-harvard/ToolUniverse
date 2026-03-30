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

# 1. Copy plugin manifest
cp -r "$PLUGIN_SRC/.claude-plugin" "$DIST_DIR/"
echo "  [+] Plugin manifest"

# 2. Copy MCP config
cp "$PLUGIN_SRC/.mcp.json" "$DIST_DIR/"
echo "  [+] MCP server config (auto-update enabled)"

# 3. Copy settings
cp "$PLUGIN_SRC/settings.json" "$DIST_DIR/"
echo "  [+] Default settings"

# 4. Copy commands
cp -r "$PLUGIN_SRC/commands" "$DIST_DIR/"
echo "  [+] Slash commands"

# 5. Copy agents
cp -r "$PLUGIN_SRC/agents" "$DIST_DIR/"
echo "  [+] Research agent"

# 6. Copy README
cp "$PLUGIN_SRC/README.md" "$DIST_DIR/"

# 7. Copy all skills (only directories with SKILL.md)
mkdir -p "$DIST_DIR/skills"
skill_count=0
for skill_dir in "$REPO_ROOT/skills"/*/; do
    dir_name=$(basename "$skill_dir")
    if [ -f "$skill_dir/SKILL.md" ] && [[ "$dir_name" == tooluniverse* ]]; then
        cp -r "$skill_dir" "$DIST_DIR/skills/$dir_name"
        skill_count=$((skill_count + 1))
    fi
done
echo "  [+] $skill_count research skills"

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
