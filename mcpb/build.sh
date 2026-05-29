#!/usr/bin/env bash
# Build tooluniverse.mcpb from mcpb/ source + repo's src/tooluniverse/.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MCPB_SRC="$REPO_ROOT/mcpb"
BUILD_DIR="$REPO_ROOT/build/mcpb"
DIST_DIR="$REPO_ROOT/dist"
OUT="$DIST_DIR/tooluniverse.mcpb"

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/src" "$DIST_DIR"

cp "$MCPB_SRC/manifest.json"   "$BUILD_DIR/manifest.json"
cp "$MCPB_SRC/pyproject.toml"  "$BUILD_DIR/pyproject.toml"
cp "$MCPB_SRC/README.md"       "$BUILD_DIR/README.md"
cp "$MCPB_SRC/icon.png"        "$BUILD_DIR/icon.png"
cp "$REPO_ROOT/.env.template"  "$BUILD_DIR/.env.template"
cp "$MCPB_SRC/src/run_stdio.py" "$BUILD_DIR/src/run_stdio.py"

# Bundle the tooluniverse package; drop dev/test/cache noise to keep size sane.
rsync -a \
  --exclude='__pycache__/' \
  --exclude='.pytest_cache/' \
  --exclude='test/' \
  --exclude='tests/' \
  --exclude='*.pyc' \
  --exclude='.DS_Store' \
  "$REPO_ROOT/src/tooluniverse/" "$BUILD_DIR/src/tooluniverse/"

# Validate manifest against official schema.
( cd "$BUILD_DIR" && npx --yes @anthropic-ai/mcpb@latest validate manifest.json )

# Pack.
rm -f "$OUT"
( cd "$BUILD_DIR" && zip -rq "$OUT" . )

SIZE=$(du -h "$OUT" | awk '{print $1}')
echo "Built $OUT ($SIZE)"
