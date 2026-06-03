#!/usr/bin/env bash
# Release a new version of the ToolUniverse Claude Code plugin.
#
# What this does:
#   1. Bump the version in all 3 manifest files (plugin.json + 2 marketplace.json)
#   2. Commit the bump
#   3. Tag the commit (vX.Y.Z)
#   4. Push commit + tag to origin
#   5. The release-plugin.yml workflow then builds the zip + creates a GitHub Release
#
# Auto-update users start receiving the new version on next Claude Code startup
# as soon as the commit lands on main (independent of the tag/release).
#
# Usage:
#   bash scripts/release-plugin.sh patch              # 1.1.11 → 1.1.12
#   bash scripts/release-plugin.sh minor              # 1.1.11 → 1.2.0
#   bash scripts/release-plugin.sh major              # 1.1.11 → 2.0.0
#   bash scripts/release-plugin.sh 1.5.0              # explicit version
#   bash scripts/release-plugin.sh patch --dry-run    # show planned changes only
#   bash scripts/release-plugin.sh patch --no-push    # bump+commit+tag, don't push

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

usage() {
    cat <<EOF
Usage: $0 <patch|minor|major|X.Y.Z> [--dry-run] [--no-push]

Examples:
    $0 patch                # next patch version
    $0 minor --dry-run      # preview minor bump without changing anything
    $0 1.2.0 --no-push      # bump, commit, tag locally; review before push

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
# releases bump pyproject/tags but not plugin.json). Computing a patch/minor
# bump from a stale manifest would produce a version that collides with an
# existing tag and make `git tag` fail, breaking the auto-release chain. Taking
# the max keeps relative bumps monotonic regardless of manifest drift.
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
echo "Current version: $CURRENT  (max of plugin.json and existing v* tags)"

case "$LEVEL" in
    patch|minor|major)
        NEW=$(python3 -c "
v = '$CURRENT'.split('.')
major, minor, patch = int(v[0]), int(v[1]), int(v[2])
level = '$LEVEL'
if level == 'major':   major, minor, patch = major + 1, 0, 0
elif level == 'minor': minor, patch = minor + 1, 0
else:                  patch += 1
print(f'{major}.{minor}.{patch}')
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
             .claude-plugin/marketplace.json; do
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
         .claude-plugin/marketplace.json; do
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
