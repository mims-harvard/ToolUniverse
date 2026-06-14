#!/usr/bin/env bash
# Release a new version of the ToolUniverse Claude Code AND Codex plugins.
#
# Versioning scheme:
#   Both plugins share the PyPI `tooluniverse` package's MAJOR.MINOR and carry
#   their own PATCH (the plugin revision). This keeps the plugin versions
#   coherent with the package they serve over MCP, while letting plugin-only
#   changes (e.g. skill edits) ship WITHOUT an empty package release:
#     - plugin-only change      -> PATCH bump      (pkg 1.2.x -> plugin 1.2.18 → 1.2.19)
#     - package MAJOR.MINOR moves-> reset to .0     (pkg 1.3.0  -> plugin 1.3.0)
#   The package keeps its own independent PyPI release line (pyproject + vX.Y.Z
#   tags); a plugin release never bumps the package.
#
# What this does:
#   1. Bump the version in all 4 plugin manifests:
#        plugin/.claude-plugin/plugin.json, plugin/.claude-plugin/marketplace.json,
#        .claude-plugin/marketplace.json, plugins/tooluniverse/.codex-plugin/plugin.json
#      (absent manifests in the current layout are skipped)
#   2. Commit the bump
#   3. Tag the commit (vX.Y.Z)
#   4. Push commit + tag to origin
#   5. The release-plugin.yml workflow then builds the zip + creates a GitHub Release
#
# Users receive the new version automatically: Claude Code on the version bump
# (next startup), Codex on the git push (startup marketplace auto-upgrade).
#
# Usage:
#   bash scripts/release-plugin.sh auto               # next plugin revision (tracks the package)
#   bash scripts/release-plugin.sh patch              # same as auto (level is advisory only)
#   bash scripts/release-plugin.sh 1.3.0              # explicit version (manual override)
#   bash scripts/release-plugin.sh auto --dry-run     # show planned changes only
#   bash scripts/release-plugin.sh auto --no-push     # bump+commit+tag, don't push

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

usage() {
    cat <<EOF
Usage: $0 <auto|patch|minor|major|X.Y.Z> [--dry-run] [--no-push]

The plugin version tracks the PyPI package's MAJOR.MINOR and bumps its own PATCH.
auto/patch/minor/major all do the same thing (next plugin revision); pass an
explicit X.Y.Z only to override manually.

Examples:
    $0 auto                 # next plugin revision (tracks the package MAJOR.MINOR)
    $0 auto --dry-run       # preview the bump without changing anything
    $0 1.3.0 --no-push      # explicit version; bump, commit, tag locally for review

Without --no-push, this script pushes commit + tag to origin and triggers the
release workflow.

Full reference (all 3 release paths, what gets bumped, safety mechanisms):
  scripts/RELEASING.md
EOF
    exit 1
}

LEVEL="${1:-}"
case "$LEVEL" in
    -h|--help|help)
        usage ;;
    "")
        usage ;;
esac

DRY_RUN=0
NO_PUSH=0
shift
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        --no-push) NO_PUSH=1 ;;
        *) echo "Unknown flag: $arg"; usage ;;
    esac
done

# Baseline = the highest of the manifest version and any existing vX.Y.Z git tag.
# The plugin manifest can drift BEHIND the released tag line (e.g. PyPI-driven
# releases bump pyproject/tags but not plugin.json). Taking the max keeps the
# plugin PATCH (revision) monotonic and avoids colliding with an existing tag.
CURRENT=$(python3 -c "
import json, re, subprocess
def parse(v):
    m = re.match(r'^(\d+)\.(\d+)\.(\d+)$', v)
    return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)
versions = [json.load(open('plugin/.claude-plugin/plugin.json'))['version']]
tags = subprocess.run(['git', 'tag', '--list', 'v*'],
                      capture_output=True, text=True).stdout.split()
versions += [t[1:] for t in tags if re.match(r'^v\d+\.\d+\.\d+$', t)]
print(max(versions, key=parse))
")
echo "Current plugin version: $CURRENT  (max of plugin.json and existing v* tags)"

case "$LEVEL" in
    patch|minor|major|auto)
        # The plugin version tracks the PyPI package's MAJOR.MINOR and owns its
        # PATCH (the plugin revision). The patch/minor/major argument is ignored:
        # whether the plugin moves to a new MAJOR.MINOR is decided by the package,
        # not by this script. A plugin-only change is always a PATCH bump, so it
        # ships without forcing an (empty) package release.
        NEW=$(python3 -c "
import re, tomllib
def parse(v):
    m = re.match(r'^(\d+)\.(\d+)\.(\d+)$', v)
    return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)
pkg = tomllib.load(open('pyproject.toml', 'rb'))['project']['version']
pmaj, pmin = (int(x) for x in re.match(r'^(\d+)\.(\d+)', pkg).groups())
cmaj, cmin, cpatch = parse('$CURRENT')
if (cmaj, cmin) == (pmaj, pmin):
    # Same line as the package -> next plugin revision.
    print(f'{pmaj}.{pmin}.{cpatch + 1}')
elif (pmaj, pmin) > (cmaj, cmin):
    # Package advanced its MAJOR.MINOR -> resync the plugin to it.
    print(f'{pmaj}.{pmin}.0')
else:
    # Plugin already ahead of the package line (package not yet released for it);
    # stay on the current line and bump the revision.
    print(f'{cmaj}.{cmin}.{cpatch + 1}')
")
        ;;
    [0-9]*.[0-9]*.[0-9]*)
        if [[ ! "$LEVEL" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            echo "Error: '$LEVEL' is not a valid X.Y.Z version" >&2
            exit 1
        fi
        NEW="$LEVEL"
        ;;
    *)
        echo "Error: '$LEVEL' is not a valid level or version" >&2
        usage
        ;;
esac

if [ "$NEW" = "$CURRENT" ]; then
    echo "Error: new version equals current version ($NEW). Nothing to do." >&2
    exit 1
fi

if git rev-parse -q --verify "refs/tags/v$NEW" >/dev/null; then
    echo "Error: tag v$NEW already exists. Choose a higher version." >&2
    exit 1
fi

echo "New version:     $NEW"
echo "Tag will be:     v$NEW"
echo

BRANCH=$(git branch --show-current)
echo "Current branch:  $BRANCH"

if [ -n "$(git status --porcelain)" ]; then
    echo "Error: working tree has uncommitted changes. Commit or stash first." >&2
    git status --short >&2
    exit 1
fi

if [ "$DRY_RUN" -eq 1 ]; then
    echo
    echo "(--dry-run) Would change (absent manifests are skipped):"
    for f in plugin/.claude-plugin/plugin.json \
             plugin/.claude-plugin/marketplace.json \
             .claude-plugin/marketplace.json \
             plugins/tooluniverse/.codex-plugin/plugin.json; do
        [ -f "$f" ] && echo "  $f   $CURRENT → $NEW" || echo "  $f   (absent, skipped)"
    done
    echo "  Then commit \"Release v$NEW\", tag v$NEW, push to origin/$BRANCH"
    exit 0
fi

python3 - <<EOF
import json, pathlib
new = "$NEW"
files = [
    ("plugin/.claude-plugin/plugin.json",       "version"),
    ("plugin/.claude-plugin/marketplace.json",  "metadata.version"),
    (".claude-plugin/marketplace.json",         "metadata.version"),
    ("plugins/tooluniverse/.codex-plugin/plugin.json", "version"),
]
for path, field in files:
    p = pathlib.Path(path)
    if not p.exists():
        # Not all manifests exist in every layout; skip rather than crash.
        print(f"  skip (absent) {path}")
        continue
    data = json.loads(p.read_text())
    if field == "version":
        data["version"] = new
    elif field == "metadata.version":
        data.setdefault("metadata", {})["version"] = new
    p.write_text(json.dumps(data, indent=2) + "\n")
    print(f"  bumped {path}")
EOF

echo
for f in plugin/.claude-plugin/plugin.json \
         plugin/.claude-plugin/marketplace.json \
         .claude-plugin/marketplace.json \
         plugins/tooluniverse/.codex-plugin/plugin.json; do
    [ -f "$f" ] && git add "$f"
done
git commit -m "Release v$NEW"
git tag -a "v$NEW" -m "v$NEW"
echo
echo "Created commit + tag v$NEW locally."

if [ "$NO_PUSH" -eq 1 ]; then
    echo
    echo "(--no-push) Stopping here. To finish the release manually:"
    echo "  git push origin $BRANCH && git push origin v$NEW"
    exit 0
fi

echo
echo "Pushing to origin..."
git push origin "$BRANCH"
git push origin "v$NEW"
echo
echo "✓ Released v$NEW"
echo "  - Auto-update users will receive it on next Claude Code startup"
echo "  - GitHub Release zip will be built and attached by the workflow:"
echo "    https://github.com/mims-harvard/ToolUniverse/actions/workflows/release-plugin.yml"
