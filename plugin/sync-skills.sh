#!/usr/bin/env bash
# Rebuild the bundled skill copies for BOTH plugin packagings as FILTERED COPIES
# of ../skills/ — user-facing skills only:
#   - plugin/skills/                 (Claude Code plugin) — all user-facing skills
#   - plugins/tooluniverse/skills/   (Codex plugin)       — same set, minus the
#                                                           Claude-Code-specific
#                                                           skills in CODEX_EXCLUDE
#
# Includes: tooluniverse, tooluniverse-*, setup-tooluniverse
# Excludes (per-skill): test_*.py, *_test.py, evals/, __pycache__/, *.pyc, .pytest_cache/,
#                      .coverage*, coverage.xml, htmlcov/, .mypy_cache/, .ruff_cache/,
#                      .DS_Store
#
# WHY copies instead of symlinks: the public marketplace.json points users to
# `./plugin` and Claude Code clones the repo. With symlinks, users got the
# dev-time skills/* tree including test files (some of which referenced our
# internal benchmark by name). Materializing filtered copies makes each
# plugin's skills/ a self-contained, clean deliverable.
#
# Run after adding/removing/editing skills in ../skills/. Idempotent.

set -euo pipefail

cd "$(dirname "$0")"
REPO_ROOT="$(cd .. && pwd)"

# Claude-Code-specific skills that should NOT ship in the Codex packaging
# (space-separated). The Codex client is a different host, so a skill about
# installing the Claude Code plugin would only confuse Codex users.
CODEX_EXCLUDE="tooluniverse-claude-code-plugin"

# Rebuild one destination skills/ dir from $REPO_ROOT/skills.
#   $1 = destination directory (recreated from scratch)
#   $2 = optional space-separated list of skill names to skip
sync_skills_into() {
  local dest="$1"
  local skip=" ${2:-} "
  rm -rf "$dest"
  mkdir -p "$dest"
  local count=0
  for dir in "$REPO_ROOT"/skills/tooluniverse "$REPO_ROOT"/skills/tooluniverse-* "$REPO_ROOT"/skills/setup-tooluniverse; do
    [ -d "$dir" ] || continue
    # Skip directories that aren't real skills (no SKILL.md). Catches accidental
    # matches like `tooluniverse-*-workspace/` (skill-evaluator output dirs).
    [ -f "$dir/SKILL.md" ] || continue
    local name
    name=$(basename "$dir")
    [[ "$skip" == *" $name "* ]] && continue
    rsync -a \
      --exclude='test_*.py' \
      --exclude='*_test.py' \
      --exclude='evals/' \
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
      "$dir"/ "$dest/$name/"
    count=$((count + 1))
  done
  echo "  $dest -> $count skills"
}

echo "Syncing user-facing skills (filtered) into both plugin packagings:"
sync_skills_into "$REPO_ROOT/plugin/skills"
sync_skills_into "$REPO_ROOT/plugins/tooluniverse/skills" "$CODEX_EXCLUDE"
