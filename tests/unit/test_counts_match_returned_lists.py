"""A reported count must describe the list the caller actually receives.

Returning `"model_count": len(models)` beside `models[:30]` tells a reader
that 324 models were handed over when 30 were. This scans the tool sources
for that shape so it cannot reappear silently.

A site is acceptable when it either counts the truncated list, or discloses
the cut some other way (a `*_truncated` flag, or a `total_*` sibling).
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

SRC = Path(__file__).resolve().parents[2] / "src/tooluniverse"

COUNT = re.compile(r'^\s*"([a-z_]*count)":\s*(?:int\()?len\((\w+)\)')
SLICED = re.compile(r'^\s*"([a-z_]+)":\s*(\w+)\[:\s*(\d+)\s*\]')


def _offenders():
    bad = []
    for path in sorted(SRC.glob("*.py")):
        lines = path.read_text(errors="ignore").splitlines()
        for i, line in enumerate(lines):
            m = COUNT.match(line)
            if not m or m.group(1).startswith("total"):
                continue
            var = m.group(2)
            near = range(max(0, i - 3), min(i + 4, len(lines)))
            sliced = any(
                (s := SLICED.match(lines[j])) and s.group(2) == var for j in near
            )
            if not sliced:
                continue
            context = "\n".join(lines[max(0, i - 5) : i + 6])
            disclosed = re.search(r'"[a-z_]*truncated"|"total_[a-z_]+"', context)
            if not disclosed:
                bad.append(f"{path.name}:{i + 1} {m.group(1)} = len({var})")
    return bad


def test_no_count_describes_an_untruncated_list():
    offenders = _offenders()
    assert not offenders, (
        "these report a count of the full list while returning a slice of it:\n  "
        + "\n  ".join(offenders)
    )
