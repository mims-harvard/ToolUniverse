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

# 7. Copy skills — ESSENTIAL skills only
# The router + key sub-skills. Keeping the list small so the agent's
# context isn't overwhelmed by 100+ skill names.
#
# The router handles dispatching to sub-skills. All sub-skills have
# disable-model-invocation: true + user-invocable: false, but their
# names still appear in the agent's skill list. Fewer = better routing.
ESSENTIAL_SKILLS=(
    # Router (always visible, handles all dispatching)
    "tooluniverse"

    # Computational analysis (BixBench-critical)
    "tooluniverse-rnaseq-deseq2"
    "tooluniverse-statistical-modeling"
    "tooluniverse-gene-enrichment"
    "tooluniverse-phylogenetics"
    "tooluniverse-variant-analysis"
    "tooluniverse-crispr-screen-analysis"
    "tooluniverse-single-cell"

    # Research skills (real user workflows)
    "tooluniverse-precision-oncology"
    "tooluniverse-drug-target-validation"
    "tooluniverse-drug-research"
    "tooluniverse-disease-research"
    "tooluniverse-pharmacovigilance"
    "tooluniverse-target-research"
    "tooluniverse-literature-deep-research"
    "tooluniverse-drug-drug-interaction"
    "tooluniverse-rare-disease-diagnosis"
    "tooluniverse-gene-disease-association"

    # Setup
    "tooluniverse-claude-code-plugin"
    "tooluniverse-custom-tool"
)

mkdir -p "$DIST_DIR/skills"
skill_count=0
for skill_name in "${ESSENTIAL_SKILLS[@]}"; do
    skill_dir="$REPO_ROOT/skills/$skill_name"
    if [ -d "$skill_dir" ] && [ -f "$skill_dir/SKILL.md" ]; then
        cp -r "$skill_dir" "$DIST_DIR/skills/$skill_name"
        skill_count=$((skill_count + 1))
    else
        echo "  [!] Missing skill: $skill_name"
    fi
done
echo "  [+] $skill_count essential skills (of $(ls -d "$REPO_ROOT/skills"/tooluniverse-*/ 2>/dev/null | wc -l | tr -d ' ') total)"

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
