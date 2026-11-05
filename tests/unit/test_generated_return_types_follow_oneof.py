"""A generated wrapper's return type should say what the schema says.

`generate_tools` asked the schema for a top-level `type`. A schema that lists
alternatives under `oneOf` has none, so the question returned "" and every such
tool was annotated `Any` -- 1,594 of them, and 1,508 of the repo's 2,890
wrappers returned bare `Any` as a result.

The branches do carry types, and a union of them says more than `Any`: a tool
whose result is an object on success and an error envelope on failure is
`dict[str, Any]` either way, and one that returns a list or an envelope is
`list[Any] | dict[str, Any]`.

The fallback stays `Any` whenever a branch declares no type at all, because a
guess there would be worse than silence.
"""

import json
from pathlib import Path

import pytest

from tooluniverse.generate_tools import _return_type_for

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "src" / "tooluniverse" / "data"
TOOLS = ROOT / "src" / "tooluniverse" / "tools"


@pytest.mark.parametrize(
    "schema,expected",
    [
        ({"type": "array"}, "list[Any]"),
        ({"type": "object"}, "dict[str, Any]"),
        ({"type": ["string", "null"]}, "Optional[str]"),
        # every branch an object -> one object type, not a union of two
        ({"oneOf": [{"type": "object"}, {"type": "object"}]}, "dict[str, Any]"),
        # the common success/error pair
        (
            {"oneOf": [{"type": "array"}, {"type": "object"}]},
            "list[Any] | dict[str, Any]",
        ),
        # nullability is collected once, not repeated per branch
        (
            {"oneOf": [{"type": ["object", "null"]}, {"type": "object"}]},
            "Optional[dict[str, Any]]",
        ),
        ({"oneOf": [{"type": "string"}, {"type": "object"}]}, "str | dict[str, Any]"),
        # a branch constraining only properties still describes an object
        ({"oneOf": [{"properties": {"a": {}}}, {"type": "object"}]}, "dict[str, Any]"),
        # a branch with no type at all: say Any rather than guess
        ({"oneOf": [{"description": "x"}, {"type": "object"}]}, "Any"),
        ({"oneOf": []}, "Any"),
        ({}, "Any"),
    ],
)
def test_the_type_follows_the_schema(schema, expected):
    assert _return_type_for(schema) == expected


def _schemas():
    for path in sorted(DATA.glob("*.json")):
        try:
            entries = json.loads(path.read_text())
        except Exception:
            continue
        for entry in entries if isinstance(entries, list) else []:
            if isinstance(entry, dict) and isinstance(entry.get("return_schema"), dict):
                yield entry["name"], entry["return_schema"]


# A tempting third assertion -- that every wrapper on disk matches what the
# generator would emit -- is deliberately absent. `build_tools` only writes
# wrappers for tools that LOAD, and which tools load depends on the optional
# dependencies installed (2,743 here, 2,729 on CI). Comparing every wrapper
# against its config therefore fails for tools this environment cannot load,
# whose wrappers were last written elsewhere. CI already enforces the real
# invariant in the environment that matters, by running the generators and
# failing if the commit does not carry what they rewrite.


def test_oneof_tools_are_no_longer_all_any():
    """The point of the change: a union is available for most of them."""
    anys = typed = 0
    for name, schema in _schemas():
        if not schema.get("oneOf"):
            continue
        if _return_type_for(schema) == "Any":
            anys += 1
        else:
            typed += 1
    assert typed > 1000, (typed, anys)
