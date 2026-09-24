#!/usr/bin/env bash
# Build tooluniverse.mcpb from the files in mcpb/. The ToolUniverse package
# itself is not copied in: the bundle declares it as a dependency so a release
# reaches users without a new directory submission (see mcpb/pyproject.toml).
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
cp "$MCPB_SRC/.python-version" "$BUILD_DIR/.python-version"
cp "$MCPB_SRC/README.md"       "$BUILD_DIR/README.md"
cp "$MCPB_SRC/icon.png"        "$BUILD_DIR/icon.png"
cp "$REPO_ROOT/.env.template"  "$BUILD_DIR/.env.template"
cp "$MCPB_SRC/src/run_stdio.py" "$BUILD_DIR/src/run_stdio.py"

# The package itself is NOT copied in. mcpb/pyproject.toml declares
# "tooluniverse" as a dependency and the manifest launches uv with
# --upgrade-package tooluniverse, so each release reaches users at their next
# launch instead of requiring a rebuilt bundle and a fresh directory
# submission. See the comment in mcpb/pyproject.toml.

# Guard: the bundle version must track the package release version. Without this
# the published bundle can silently lag the root pyproject.toml after a bump.
ROOT_VER=$(grep -m1 '^version' "$REPO_ROOT/pyproject.toml" | sed -E 's/.*"([^"]+)".*/\1/')
BUNDLE_VER=$(grep -m1 '^version' "$MCPB_SRC/pyproject.toml" | sed -E 's/.*"([^"]+)".*/\1/')
MANIFEST_VER=$(python3 -c "import json; print(json.load(open('$MCPB_SRC/manifest.json'))['version'])")
if [ "$ROOT_VER" != "$BUNDLE_VER" ] || [ "$ROOT_VER" != "$MANIFEST_VER" ]; then
  echo "ERROR: version drift — root=$ROOT_VER mcpb/pyproject=$BUNDLE_VER mcpb/manifest=$MANIFEST_VER" >&2
  echo "Bump mcpb/manifest.json and mcpb/pyproject.toml to match the root release." >&2
  exit 1
fi

# Guard: the declared floor must be a release that exists, so the bundle cannot
# ship pinned to a version PyPI has never seen. Comparing against the root
# version is enough -- publish-pypi.yml publishes it from the same commit.
FLOOR=$(python3 - "$MCPB_SRC/pyproject.toml" <<'PYEOF'
import re, sys
text = open(sys.argv[1]).read()
match = re.search(r'"tooluniverse(?:\[[^\]]*\])?>=([0-9][^,"]*)', text)
print(match.group(1) if match else "")
PYEOF
)
if [ -z "$FLOOR" ]; then
  echo "ERROR: mcpb/pyproject.toml declares no tooluniverse floor" >&2
  exit 1
fi
if [ "$(printf '%s\n%s\n' "$FLOOR" "$ROOT_VER" | sort -V | head -1)" != "$FLOOR" ]; then
  echo "ERROR: dependency floor $FLOOR is ahead of the release being built ($ROOT_VER)" >&2
  exit 1
fi
if ! grep -qE '"tooluniverse(\[[^]]*\])?>=[^"]*<2"' "$MCPB_SRC/pyproject.toml"; then
  echo "ERROR: the tooluniverse dependency needs a major-version ceiling (<2)" >&2
  echo "Without it a future major release reaches users unreviewed." >&2
  exit 1
fi

# Validate against MCPB 0.4. An installed CLI permits offline/reproducible builds.
if [ -n "${MCPB_CLI:-}" ]; then
  ( cd "$BUILD_DIR" && "$MCPB_CLI" validate manifest.json )
else
  ( cd "$BUILD_DIR" && npx --yes @anthropic-ai/mcpb@2.1.2 validate manifest.json )
fi

# Pack.
rm -f "$OUT"
( cd "$BUILD_DIR" && zip -rq "$OUT" . )

SIZE=$(du -h "$OUT" | awk '{print $1}')
echo "Built $OUT ($SIZE)"
