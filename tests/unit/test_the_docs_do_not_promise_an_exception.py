"""The docs told users to catch exceptions a tool call never raises.

`docs/guide/coding_api.rst` had an "Error Handling" section built on
`except ToolValidationError`, and the SDK skill and MCP tasks guide had the same
shape with `ToolError` / `ToolUnavailableError`. Nothing in the call path raises
any of them: `run_one_function` converts them with `_create_dual_format_error`
and returns `{"status", "error", "error_details"}`. Across the whole package
there are zero `raise ToolError` and zero `raise ToolValidationError` sites, and
the single `raise ToolUnavailableError` carries a comment saying its caller's
`except Exception` turns it into that same envelope.

So the `except` never fired, the error dict fell through as if it were data, and
a reader following the guide shipped that. The REFERENCE.md version was worse:
its `fallback_tool` hung off `except ToolUnavailableError`, so the fallback was
unreachable. The MCP guide listed `except ToolUnavailableError` after
`except ToolError`, its own base class, so that leg was unreachable twice over.

The docs now branch on the returned value and read `error_details["type"]` for
the error class name. These tests keep the two sides tied together: no
documented `except` on a tool call, and the fields the docs now tell people to
read are really there.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

# An `except` clause naming one of the tool exceptions, i.e. the dead pattern.
# Prose that merely mentions `except ToolValidationError` to explain why it does
# not work is fine, so this only matches a real statement: start of line
# (optionally indented) and a colon or `as` after the name.
DEAD_EXCEPT = re.compile(
    r"^[ \t]*except +\(?\s*Tool[A-Za-z]*Error[^\n]*?(?::|\bas\b)", re.M
)

SEARCH_ROOTS = (
    ROOT / "docs",
    ROOT / "skills",
    ROOT / "plugin" / "skills",
    ROOT / "plugins" / "tooluniverse" / "skills",
    ROOT / "examples",
)


def _documents():
    for root in SEARCH_ROOTS:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if path.suffix not in {".md", ".rst", ".py", ".txt"}:
                continue
            # Translation catalogues mirror whatever the English said; they are
            # regenerated from it and carry no instructions of their own.
            if "locale" in path.parts:
                continue
            yield path


def test_no_document_tells_a_reader_to_except_a_tool_error():
    offenders = []
    for path in _documents():
        text = path.read_text("utf-8", errors="replace")
        for match in DEAD_EXCEPT.finditer(text):
            line = text[: match.start()].count("\n") + 1
            offenders.append(
                f"{path.relative_to(ROOT)}:{line}: {match.group(0).strip()}"
            )

    assert not offenders, (
        "a tool call returns its error and never raises these, so this "
        f"`except` catches nothing: {offenders}"
    )


def test_the_package_still_does_not_raise_them_from_a_call():
    """The premise. If this ever changes, the docs above need revisiting."""
    src = ROOT / "src" / "tooluniverse"
    raises = []
    for path in sorted(src.rglob("*.py")):
        for match in re.finditer(
            r"^[ \t]*raise +(Tool[A-Za-z]*Error)", path.read_text("utf-8"), re.M
        ):
            raises.append(f"{path.relative_to(ROOT)}: {match.group(1)}")

    # encode_tool.py raises ToolUnavailableError on purpose, and says in a
    # comment that the caller's `except Exception` converts it to an envelope.
    assert [r for r in raises if "encode_tool.py" not in r] == [], raises


@pytest.mark.parametrize(
    "call,expected_type",
    [
        ({"name": "no_such_tool_at_all", "arguments": {}}, None),
        (
            {"name": "ClinGen_dosage_region_search", "arguments": {"chromosome": 123}},
            "ToolValidationError",
        ),
    ],
)
def test_the_fields_the_docs_tell_people_to_read_are_there(call, expected_type):
    from tooluniverse import ToolUniverse

    tu = ToolUniverse()
    tu.load_tools(include_tools=["ClinGen_dosage_region_search"])

    result = tu.run(call)  # must not raise

    assert isinstance(result, dict)
    assert result.get("status") == "error"
    assert result.get("error")
    details = result.get("error_details") or {}
    if expected_type:
        assert details.get("type") == expected_type
        assert isinstance(details.get("next_steps"), list) and details["next_steps"]
        assert "retriable" in details
