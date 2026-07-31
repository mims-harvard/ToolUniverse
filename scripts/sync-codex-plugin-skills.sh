#!/usr/bin/env bash
set -euo pipefail

# Rebuild plugins/tooluniverse/skills/ as filtered copies of the canonical
# root skills/ tree. Do not edit plugins/tooluniverse/skills/ directly.

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# Destination defaults to the tracked plugin copy but can be redirected (e.g. to
# a temp dir) so tests can exercise the sync without mutating tracked files.
DEST_DIR="${CODEX_PLUGIN_SKILLS_DEST:-$REPO_ROOT/plugins/tooluniverse/skills}"

# Resolve a known-good interpreter for the description-compaction step. PyYAML is
# a declared dependency; prefer the repo venv (or an active virtualenv) over a
# bare `python3` on PATH that may lack PyYAML. If none of these has PyYAML, the
# compaction script fails loudly rather than corrupting skill descriptions.
if [ -n "${CODEX_PLUGIN_PYTHON:-}" ]; then
    PYTHON_BIN="$CODEX_PLUGIN_PYTHON"
elif [ -n "${VIRTUAL_ENV:-}" ] && [ -x "$VIRTUAL_ENV/bin/python" ]; then
    PYTHON_BIN="$VIRTUAL_ENV/bin/python"
elif [ -x "$REPO_ROOT/.venv/bin/python" ]; then
    PYTHON_BIN="$REPO_ROOT/.venv/bin/python"
else
    PYTHON_BIN="python3"
fi

rm -rf "$DEST_DIR"
mkdir -p "$DEST_DIR"

count=0
for skill_dir in "$REPO_ROOT/skills/tooluniverse" "$REPO_ROOT"/skills/tooluniverse-* "$REPO_ROOT/skills/setup-tooluniverse"; do
    [ -d "$skill_dir" ] || continue
    [ -f "$skill_dir/SKILL.md" ] || continue

    name="$(basename "$skill_dir")"

    # Claude-specific install docs are useful in the Claude plugin, but not in
    # the Codex plugin's skill router surface. Same for Claude Science install
    # docs (different host entirely: conda env + host.skills.* API, no
    # MCP/uvx/plugin marketplace involved).
    if [ "$name" = "tooluniverse-claude-code-plugin" ] || [ "$name" = "tooluniverse-cs-setup" ]; then
        continue
    fi

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
        "$skill_dir"/ "$DEST_DIR/$name/"

    # Codex plugin validation currently rejects Claude's hidden-subskill
    # marker. Keep the canonical source unchanged and normalize only the
    # generated Codex copy.
    tmp_file="$(mktemp)"
    awk '$0 != "disable-model-invocation: true" && $0 != "disable-model-invocation: false" { print }' \
        "$DEST_DIR/$name/SKILL.md" > "$tmp_file"
    mv "$tmp_file" "$DEST_DIR/$name/SKILL.md"

    # Codex rejects skill descriptions over 1024 characters. Keep the root
    # skill source untouched and compact only the generated plugin copy. The
    # compaction runs as a standalone script (not an inline heredoc) so it is
    # unit-testable and so a missing PyYAML fails loudly instead of silently
    # rewriting the description to a bare YAML block-scalar indicator.
    "$PYTHON_BIN" "$REPO_ROOT/scripts/compact_codex_skill_description.py" \
        "$DEST_DIR/$name/SKILL.md"

    count=$((count + 1))
done

echo "Copied $count Codex plugin skills into plugins/tooluniverse/skills/"
