#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLUGIN_SRC="$REPO_ROOT/plugins/tooluniverse"
# Both destinations can be redirected so tests (and dry runs) can build the
# plugin into a temp tree without regenerating tracked files in place.
SKILLS_DEST="${CODEX_PLUGIN_SKILLS_DEST:-$PLUGIN_SRC/skills}"
DIST_DIR="${CODEX_PLUGIN_DIST:-$REPO_ROOT/dist/tooluniverse-codex-plugin}"

echo "Building ToolUniverse Codex plugin..."

CODEX_PLUGIN_SKILLS_DEST="$SKILLS_DEST" "$REPO_ROOT/scripts/sync-codex-plugin-skills.sh"

rm -rf "$DIST_DIR"
mkdir -p "$DIST_DIR"

mkdir -p "$DIST_DIR/.codex-plugin"
cp "$PLUGIN_SRC/.codex-plugin/plugin.json" "$DIST_DIR/.codex-plugin/"
echo "  [+] Codex plugin manifest"

cp "$PLUGIN_SRC/.mcp.json" "$DIST_DIR/"
echo "  [+] MCP server config"

cp -r "$SKILLS_DEST" "$DIST_DIR/skills"
echo "  [+] Skills"

cp "$PLUGIN_SRC/README.md" "$DIST_DIR/"
if [ -f "$REPO_ROOT/LICENSE" ]; then
    cp "$REPO_ROOT/LICENSE" "$DIST_DIR/"
fi
echo "  [+] README + LICENSE"

total_files=$(find "$DIST_DIR" -type f | wc -l | tr -d ' ')
total_size=$(du -sh "$DIST_DIR" | cut -f1)

echo ""
echo "Codex plugin built successfully."
echo "  Location: $DIST_DIR"
echo "  Files: $total_files"
echo "  Size: $total_size"
