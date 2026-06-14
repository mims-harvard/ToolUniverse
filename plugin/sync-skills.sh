#!/usr/bin/env bash
# Rebuild the bundled skill copies for BOTH plugin packagings from the canonical
# ../skills/ tree, then keep them in step:
#   - plugin/skills/                 (Claude Code plugin) — rebuilt here
#   - plugins/tooluniverse/skills/   (Codex plugin)       — delegated to
#                                     scripts/sync-codex-plugin-skills.sh
#
# Claude side — FILTERED COPIES of ../skills/, user-facing skills only.
# Includes: tooluniverse, tooluniverse-*, setup-tooluniverse
# Excludes (per-skill): test_*.py, *_test.py, evals/, __pycache__/, *.pyc, .pytest_cache/,
#                      .coverage*, coverage.xml, htmlcov/, .mypy_cache/, .ruff_cache/,
#                      .DS_Store
#
# WHY copies instead of symlinks: the public marketplace.json points users to
# `./plugin` and Claude Code clones the repo. With symlinks, users got the
# dev-time skills/* tree including test files (some of which referenced our
# internal benchmark by name). Materializing filtered copies makes
# plugin/skills/ a self-contained, clean deliverable.
#
# The Codex copy needs extra Codex-specific normalizations (it drops the
# disable-model-invocation marker Codex validation rejects and compacts
# descriptions over Codex's 1024-char limit), so that logic lives in its own
# script; this one invokes it so a single command keeps both packagings in sync.
#
# Run after adding/removing/editing skills in ../skills/. Idempotent.

set -euo pipefail

cd "$(dirname "$0")"
REPO_ROOT="$(cd .. && pwd)"

# Codex-host-specific skills that should NOT ship in the Claude packaging
# (mirror of how the Codex sync drops tooluniverse-claude-code-plugin).
CLAUDE_EXCLUDE="tooluniverse-codex-plugin"

# Recreate plugin/skills/ from scratch (Claude packaging — all user-facing skills)
rm -rf skills
mkdir skills

count=0
for dir in ../skills/tooluniverse ../skills/tooluniverse-* ../skills/setup-tooluniverse; do
  [ -d "$dir" ] || continue
  # Skip directories that aren't real skills (no SKILL.md). Catches
  # accidental matches like `tooluniverse-*-workspace/` which are skill-
  # evaluator output directories, not skills.
  [ -f "$dir/SKILL.md" ] || continue
  name=$(basename "$dir")
  [[ " $CLAUDE_EXCLUDE " == *" $name "* ]] && continue
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
    "$dir"/ "skills/$name/"
  count=$((count + 1))
done

echo "Copied $count user-facing skills (filtered) into plugin/skills/"

# Codex packaging — same source, with Codex-specific normalizations applied.
bash "$REPO_ROOT/scripts/sync-codex-plugin-skills.sh"
