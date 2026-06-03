#!/usr/bin/env bash
# Rebuild plugin/skills/ as FILTERED COPIES of ../skills/ — user-facing skills only.
#
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
# Run after adding/removing/editing skills in ../skills/. Idempotent.

set -euo pipefail

cd "$(dirname "$0")"

# Recreate skills/ from scratch
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
