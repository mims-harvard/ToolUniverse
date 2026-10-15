#!/usr/bin/env python3
"""Flag deprecated wording in the user-facing docs (Phase A of devtu-docs-quality).

Checks ``docs/``, ``README.md`` and ``skills/`` for text that must not reappear:

* ``python -m tooluniverse.server``  -> use the ``tooluniverse-server`` command
* ``600+ tools`` / ``750+ tools``     -> the docs say "1000+ tools"

Files that *describe* these checks (``docs/dev_docs/`` and the ``devtu-docs-quality``
skill, whose examples quote the deprecated text on purpose) are skipped, as is any line
carrying ``noqa: docs-validate``.

Usage:
    python scripts/validate_documentation.py
Exit status is 1 when anything is found.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DEPRECATED_PATTERNS = [
    (re.compile(r"python -m tooluniverse\.server"), "tooluniverse-server"),
    (re.compile(r"\b600\+?\s+tools"), "1000+ tools"),
    (re.compile(r"\b750\+?\s+tools"), "1000+ tools"),
]
SCAN = ["docs", "README.md", "skills"]
SUFFIXES = (".md", ".rst", ".txt")
SKIP_PARTS = ("docs/dev_docs/", "skills/devtu-docs-quality/")
SUPPRESS = "noqa: docs-validate"


def iter_files(root=ROOT):
    for entry in SCAN:
        path = root / entry
        candidates = [path] if path.is_file() else sorted(path.rglob("*"))
        for file in candidates:
            rel = file.relative_to(root).as_posix()
            if file.is_file() and file.suffix in SUFFIXES:
                if not any(part in rel for part in SKIP_PARTS):
                    yield file, rel


def check_text(text):
    """Return [(line number, matched text, replacement)] for one document."""
    problems = []
    for number, line in enumerate(text.splitlines(), 1):
        if SUPPRESS in line:
            continue
        for pattern, replacement in DEPRECATED_PATTERNS:
            for match in pattern.finditer(line):
                problems.append((number, match.group(0), replacement))
    return problems


def main(root=ROOT):
    total = 0
    for file, rel in iter_files(root):
        try:
            text = file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for number, found, replacement in check_text(text):
            total += 1
            print(f"{rel}:{number}: '{found}' -> use '{replacement}'")
    print(f"{total} problem(s)")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
