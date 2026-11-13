"""Documented snippets must read a tool result as {status, data, metadata}.

Filed as #869. A tool call returns the envelope, so a snippet that measures
the result with len() measures the envelope's three keys, and one that guards
with isinstance(result, list) never enters its own branch. Both failures are
silent: nothing raises, and the printed line looks like a result.

Measured on main at the time of writing, with the envelope in force:

    r = tu.run({"name": "PubMed_search_articles", ...})
    len(r)                 # 3   -- status, data, metadata
    isinstance(r, list)    # False
    r["status"]            # "success", even for a query matching nothing

docs/guide/api_keys.rst told a reader to verify their API keys with
`"success" if len(result) > 0 else "failed"`, which prints success whether or
not the key works. docs/guide/literature_search_tools_tutorial.rst guarded
four printing blocks with isinstance(result, list), so none of them could run,
and its safe_search helper returned "Unexpected result format" for every call
that succeeded.

This test does not ban a spelling. It reads each code block, finds the names
bound from tu.run(...), and fails if such a name is then used as a sequence in
the same block.
"""

import re
from pathlib import Path

import pytest

_GUIDE = Path(__file__).resolve().parents[2] / "docs" / "guide"


def _code_blocks(text):
    """Each `.. code-block:: python` body, as a list of lines."""
    lines = text.splitlines()
    out, i = [], 0
    while i < len(lines):
        if re.match(r"^\s*\.\. code-block:: python\s*$", lines[i]):
            indent = len(lines[i]) - len(lines[i].lstrip())
            body, j = [], i + 1
            while j < len(lines):
                line = lines[j]
                if line.strip() and (len(line) - len(line.lstrip())) <= indent:
                    break
                body.append(line)
                j += 1
            out.append(body)
            i = j
        else:
            i += 1
    return out


def _offences(body):
    """Names bound from tu.run(...) that are then used as a sequence."""
    names = set()
    for line in body:
        m = re.match(r"\s*(\w+)\s*=\s*tu\.run\(", line)
        if m:
            names.add(m.group(1))
    bad = []
    for name in sorted(names):
        for line in body:
            if re.match(rf"\s*{name}\s*=\s*tu\.run\(", line):
                continue
            if re.search(rf"\blen\(\s*{name}\s*\)", line) or re.search(
                rf"\bisinstance\(\s*{name}\s*,\s*list\s*\)", line
            ):
                bad.append(line.strip())
    return bad


def _rst_files():
    return sorted(_GUIDE.rglob("*.rst"))


def test_the_guide_has_code_blocks_to_check():
    assert any(_code_blocks(f.read_text(encoding="utf-8")) for f in _rst_files())


@pytest.mark.parametrize("path", _rst_files(), ids=lambda p: p.name)
def test_no_snippet_measures_the_envelope(path):
    found = []
    for body in _code_blocks(path.read_text(encoding="utf-8")):
        found.extend(_offences(body))
    assert not found, (
        f"{path.name}: a tu.run() result is used as a sequence, which measures "
        f"the envelope rather than the data: {found}"
    )


def test_the_api_key_check_can_actually_fail():
    text = (_GUIDE / "api_keys.rst").read_text(encoding="utf-8")
    checks = re.findall(r'print\("(?:PubMed|OpenTargets) test:".*', text)
    assert len(checks) == 2, f"expected the two connectivity checks, found {checks}"
    for line in checks:
        assert "len(result)" not in line, (
            "len() on the envelope is 3 whatever happened, so this prints "
            f"success unconditionally: {line}"
        )
        assert 'result.get("status")' in line, line
