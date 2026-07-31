#!/usr/bin/env python3
"""Compact an over-long skill ``description:`` in a generated Codex SKILL.md.

Codex rejects skill descriptions longer than 1024 characters, so the generated
Codex plugin copies (never the canonical ``skills/`` source) get their
``description:`` frontmatter truncated to fit. This script performs that
normalization in place on a single ``SKILL.md`` file: it reads the description,
truncates it if necessary, and rewrites it as a single JSON-quoted line.

It deliberately fails loudly rather than guessing, because a silent guess is
what previously corrupted skill descriptions:

  * PyYAML is a declared dependency (see ``pyproject.toml``). If it cannot be
    imported, the *wrong interpreter* is running the sync -- that must surface as
    an error, not be swallowed. The regex fallback below cannot read a YAML
    folded/literal block scalar, so running without PyYAML used to rewrite a
    real description down to the bare block-scalar indicator (``">-"``) and
    delete the folded text underneath.
  * If extraction ever falls back to the line regex and captures a block-scalar
    indicator (``>``, ``>-``, ``|`` ...) or an empty value, the script aborts
    instead of writing that back.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import NoReturn, Optional

# A missing PyYAML means the sync is running under the wrong interpreter. Import
# at module scope and unguarded so that failure is loud (ImportError), never a
# silent fallback to the description-destroying regex path.
import yaml

MAX_DESCRIPTION_LEN = 1024
TRUNCATED_TARGET_LEN = 1000

# YAML block-scalar indicators. A regex that reads only the ``description:`` line
# captures one of these tokens instead of the folded/literal text that lives on
# the following indented lines.
BLOCK_SCALAR_INDICATORS = frozenset({">", ">-", ">+", "|", "|-", "|+"})


def _fail(message: str) -> NoReturn:
    sys.stderr.write(f"compact_codex_skill_description: {message}\n")
    raise SystemExit(1)


def extract_description(frontmatter: str, path: Path) -> Optional[str]:
    """Return the description string, or ``None`` when there is no field to compact.

    Aborts with a non-zero exit when a description is present but cannot be read
    without guessing (empty, non-string, or a bare block-scalar indicator picked
    up by the regex fallback).
    """
    try:
        data = yaml.safe_load(frontmatter)
    except yaml.YAMLError:
        data = None

    if isinstance(data, dict):
        value = data.get("description")
        if value is None:
            # No description key at all -- nothing to compact, leave file as-is.
            return None
        if not isinstance(value, str):
            _fail(f"{path}: description is not a string ({type(value).__name__})")
        if not value.strip():
            _fail(f"{path}: description is empty")
        return value

    # YAML did not parse into a mapping; fall back to a single-line regex and
    # refuse to write anything that is obviously not the real description.
    match = re.search(r"(?m)^description:\s*(.*)$", frontmatter)
    if not match:
        return None
    candidate = match.group(1).strip().strip("\"'")
    if not candidate or candidate in BLOCK_SCALAR_INDICATORS:
        _fail(
            f"{path}: could not extract a usable description. The regex fallback "
            f"captured {candidate!r}, which is a YAML block-scalar indicator "
            f"(or empty) rather than the description text. Refusing to write it "
            f"-- doing so would destroy the description. This usually means the "
            f"sync ran under an interpreter without PyYAML; re-run with the repo "
            f"venv (source .venv/bin/activate)."
        )
    return candidate


def _truncate(description: str) -> str:
    return description[:TRUNCATED_TARGET_LEN].rsplit(" ", 1)[0].rstrip(" ,;:-") + "..."


def compact(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return
    try:
        _, frontmatter, body = text.split("---", 2)
    except ValueError:
        return

    description = extract_description(frontmatter, path)
    if description is None:
        return

    if len(description) > MAX_DESCRIPTION_LEN:
        description = _truncate(description)

    new_lines = []
    skipping_description_block = False

    for line in frontmatter.splitlines():
        if skipping_description_block:
            if line.startswith((" ", "\t")) or not line.strip():
                continue
            skipping_description_block = False

        if re.match(r"^description:\s*", line):
            new_lines.append(
                f"description: {json.dumps(description, ensure_ascii=False)}"
            )
            if re.match(r"^description:\s*[|>]", line):
                skipping_description_block = True
            continue

        new_lines.append(line)

    path.write_text("---\n" + "\n".join(new_lines) + "\n---" + body, encoding="utf-8")


def main() -> None:
    args = sys.argv[1:]
    if len(args) != 1:
        _fail("usage: compact_codex_skill_description.py <path-to-SKILL.md>")
    compact(Path(args[0]))


if __name__ == "__main__":
    main()
