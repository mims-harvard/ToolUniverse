"""Read, mask, and merge API-key values in a .env file. Stdlib only."""
from __future__ import annotations

import os
import re
from pathlib import Path

_LINE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$")


def read_env(path) -> dict:
    """Return KEY->value for a .env file (missing file -> {})."""
    path = Path(path)
    values: dict = {}
    if not path.exists():
        return values
    for line in path.read_text().splitlines():
        if line.lstrip().startswith("#"):
            continue
        m = _LINE.match(line)
        if m:
            values[m.group(1)] = m.group(2).strip()
    return values


def mask(value: str) -> str:
    """Mask a secret for display, keeping the last 4 characters."""
    if not value:
        return ""
    if len(value) <= 4:
        return "*" * len(value)
    return "*" * (len(value) - 4) + value[-4:]


def merge_env(path, updates: dict) -> None:
    """Merge updates into the .env at path, preserving unrelated lines.

    Value "" removes the key. Keys absent from updates are left as-is.
    Writes with mode 0o600.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text().splitlines() if path.exists() else []
    out, seen = [], set()
    for line in existing:
        m = None if line.lstrip().startswith("#") else _LINE.match(line)
        if m and m.group(1) in updates:
            name = m.group(1)
            seen.add(name)
            if updates[name] != "":
                out.append(f"{name}={updates[name]}")
        else:
            out.append(line)
    for name, val in updates.items():
        if name not in seen and val != "":
            out.append(f"{name}={val}")
    text = ("\n".join(out).rstrip() + "\n") if out else ""
    path.write_text(text)
    os.chmod(path, 0o600)
