#!/usr/bin/env bash
set -euo pipefail

# Rebuild plugins/tooluniverse/skills/ as filtered copies of the canonical
# root skills/ tree. Do not edit plugins/tooluniverse/skills/ directly.

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST_DIR="$REPO_ROOT/plugins/tooluniverse/skills"

rm -rf "$DEST_DIR"
mkdir -p "$DEST_DIR"

count=0
for skill_dir in "$REPO_ROOT/skills/tooluniverse" "$REPO_ROOT"/skills/tooluniverse-* "$REPO_ROOT/skills/setup-tooluniverse"; do
    [ -d "$skill_dir" ] || continue
    [ -f "$skill_dir/SKILL.md" ] || continue

    name="$(basename "$skill_dir")"

    # Claude-specific install docs are useful in the Claude plugin, but not in
    # the Codex plugin's skill router surface.
    if [ "$name" = "tooluniverse-claude-code-plugin" ]; then
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
    # skill source untouched and compact only the generated plugin copy.
    python3 - "$DEST_DIR/$name/SKILL.md" <<'PY'
import json
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
if not text.startswith("---\n"):
    raise SystemExit(0)

try:
    _, frontmatter, body = text.split("---", 2)
except ValueError:
    raise SystemExit(0)

description = None
try:
    import yaml

    data = yaml.safe_load(frontmatter)
    if isinstance(data, dict) and isinstance(data.get("description"), str):
        description = data["description"]
except Exception:
    pass

if description is None:
    match = re.search(r"(?m)^description:\s*(.*)$", frontmatter)
    if match:
        description = match.group(1).strip().strip("\"'")

if not description:
    raise SystemExit(0)

if len(description) > 1024:
    description = description[:1000].rsplit(" ", 1)[0].rstrip(" ,;:-") + "..."

new_lines = []
skipping_description_block = False

for line in frontmatter.splitlines():
    if skipping_description_block:
        if line.startswith((" ", "\t")) or not line.strip():
            continue
        skipping_description_block = False

    if re.match(r"^description:\s*", line):
        new_lines.append(f"description: {json.dumps(description, ensure_ascii=False)}")
        if re.match(r"^description:\s*[|>]", line):
            skipping_description_block = True
        continue

    new_lines.append(line)

path.write_text("---\n" + "\n".join(new_lines) + "\n---" + body, encoding="utf-8")
PY

    count=$((count + 1))
done

echo "Copied $count Codex plugin skills into plugins/tooluniverse/skills/"
