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

# Resolve once, at build time, and ship the result. Without a lock `uv run` has
# to reach the index on every launch to resolve the dependency, so an index that
# hangs stops a bundle that is already installed and working -- measured at 44 s
# to failure against a blackholed index, which Desktop shows as "Server
# disconnected". With the lock and --frozen, startup touches no network at all,
# and the update is the launcher's bounded refresh instead.
( cd "$BUILD_DIR" && uv lock --quiet )

PYTHON_PIN=$(tr -d "[:space:]" < "$MCPB_SRC/.python-version")

# The package itself is NOT copied in. mcpb/pyproject.toml declares
# "tooluniverse" as a dependency and src/run_stdio.py moves the install forward
# on its own, so each release reaches users at their next launch instead of
# requiring a rebuilt bundle and a fresh directory submission. See the comment
# in mcpb/pyproject.toml.

# Guard: the lock is resolved here, on one machine, but installed on every
# platform the manifest advertises. A dependency that publishes no wheel for one
# of them fails at install time, not at lock time -- `uv lock` happily resolves
# a version whose metadata is fine and whose wheels are not. That reaches the
# user as "Server disconnected" on a fresh install, and we would hear about it
# from them rather than from CI. --dry-run resolves the install plan for a
# target without needing that machine.
#
# --no-build is part of the check, not a detail: without it a dry-run "passes"
# for a package that has no wheel for the target but does have an sdist, because
# planning an install is not building one. uvloop is the shape to remember --
# linux and macOS wheels, an sdist, and nothing for Windows. The plain dry-run
# reported "Would install 168 packages"; with --no-build it says uvloop "has no
# binary distribution". No user of a desktop extension should need a compiler,
# so requiring a wheel everywhere is the property we actually want.
#
# The macOS floor is 14, set through MACOSX_DEPLOYMENT_TARGET because
# --python-platform carries an architecture and not an OS version. faiss-cpu
# publishes macosx_14_0 wheels and nothing older, for every release it still
# ships, so 14 is where a Mac can install without a toolchain. uv assumes a
# lower default and reports faiss-cpu as unbuildable without this.
MACOS_FLOOR=14.0
for PLATFORM in aarch64-apple-darwin x86_64-pc-windows-msvc \
                x86_64-unknown-linux-gnu aarch64-unknown-linux-gnu; do
  if ! ( cd "$BUILD_DIR" && MACOSX_DEPLOYMENT_TARGET="$MACOS_FLOOR" \
           uv sync --frozen --quiet --dry-run --no-build \
           --python "$PYTHON_PIN" --python-platform "$PLATFORM" >/dev/null 2>&1 ); then
    echo "ERROR: the locked dependencies do not install on $PLATFORM," >&2
    echo "which mcpb/manifest.json advertises. Re-run for the detail:" >&2
    echo "  (cd $BUILD_DIR && MACOSX_DEPLOYMENT_TARGET=$MACOS_FLOOR uv sync --frozen --dry-run --no-build --python $PYTHON_PIN --python-platform $PLATFORM)" >&2
    exit 1
  fi
done

# Checked, but deliberately not enforced. Both are retired configurations, and
# the fix in each case would be pinning a dependency back below the version its
# maintainers ship -- against the directory policy's own requirement that a
# local MCP server "must be built with reasonably current versions of all
# dependencies", and in aid of hardware essentially nobody still runs.
#
#   x86_64-apple-darwin      Intel Macs. cryptography stopped publishing
#                            macOS x86_64 and universal2 wheels at 49.0.0;
#                            48.0.1 was the last with them.
#   aarch64-pc-windows-msvc  Windows on ARM. epam-indigo publishes win32 and
#                            win_amd64 and no win_arm64. Unreachable today
#                            because uv ships no ARM64 Windows CPython (0.12.2
#                            offers windows-x86_64 only), so those machines get
#                            the x64 interpreter and the win_amd64 wheels:
#                              uv python list --all-platforms | grep -i windows
#                            It becomes real the day uv ships one.
for PLATFORM in x86_64-apple-darwin aarch64-pc-windows-msvc; do
  if ! ( cd "$BUILD_DIR" && MACOSX_DEPLOYMENT_TARGET="$MACOS_FLOOR" \
           uv sync --frozen --quiet --dry-run --no-build \
           --python "$PYTHON_PIN" --python-platform "$PLATFORM" >/dev/null 2>&1 ); then
    echo "NOTE: not installable on $PLATFORM without a compiler (known, see build.sh)" >&2
  fi
done

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
