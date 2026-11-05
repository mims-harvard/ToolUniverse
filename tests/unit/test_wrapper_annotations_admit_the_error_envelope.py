"""A generated wrapper's annotation has to admit the dict it can return.

A wrapper hands back `run_one_function(...)` unchanged, and that call has a
failure exit of its own: `_create_dual_format_error` answers
``{"status", "error", "error_details"}`` for an unknown tool, a parameter that
fails validation, a tool that raises, and a timeout. So every wrapper can
return a dict, whatever its `return_schema` describes.

235 annotations could not. 208 said `list[Any]`, 17 `str`, 6 `Optional[str]`
and 4 `Optional[list[Any]]`, while the tools answer the ``{status, data}``
envelope of issue #246. The failure is quiet: `for row in Tool(...)` iterates
the envelope's keys instead of the rows, raises nothing, and simply gives the
wrong answer. Checking all 235 live against their own `test_examples`
confirmed 179 wrong, 9 right, and 47 unmeasurable because the tool errored or
carried no usable example.

The fix widens the union instead of unwrapping the envelope. Returning
`result["data"]` would make the narrow annotation true and break every caller
reading `status` or `data` today -- silently, because the key would be absent
rather than raise.
"""

import re
from pathlib import Path

import pytest

from tooluniverse.generate_tools import _return_type_for, _wrapper_return_type

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "src" / "tooluniverse" / "tools"

# The line that closes a generated wrapper's signature, e.g. ") -> list[Any]:".
SIGNATURE = re.compile(r"^\) -> (.+):$", re.M)


@pytest.mark.parametrize(
    "schema,expected",
    [
        # the four shapes that were actually wrong on disk
        ({"type": "array"}, "list[Any] | dict[str, Any]"),
        ({"type": "string"}, "str | dict[str, Any]"),
        ({"type": ["string", "null"]}, "Optional[str | dict[str, Any]]"),
        ({"type": ["array", "null"]}, "Optional[list[Any] | dict[str, Any]]"),
        # Optional stays on the outside rather than being repeated per member
        (
            {"oneOf": [{"type": ["array", "null"]}]},
            "Optional[list[Any] | dict[str, Any]]",
        ),
        # already admits a dict: left exactly as it was
        ({"type": "object"}, "dict[str, Any]"),
        (
            {"oneOf": [{"type": "array"}, {"type": "object"}]},
            "list[Any] | dict[str, Any]",
        ),
        # Any already covers the error dict, and widening it would say less
        ({"oneOf": [{"description": "no type here"}]}, "Any"),
        ({}, "Any"),
    ],
)
def test_the_annotation_admits_a_dict(schema, expected):
    assert _wrapper_return_type(schema) == expected


@pytest.mark.parametrize(
    "schema",
    [{"type": "array"}, {"type": "string"}, {"type": ["string", "null"]}],
)
def test_the_schema_mapping_itself_is_left_narrow(schema):
    """`_return_type_for` answers for the schema, not for the wrapper.

    Widening it in place would be the tempting one-line version of this fix,
    and it would make the function lie about the schema -- the thing `tu test`
    validates a return against.
    """
    assert "dict[str, Any]" not in _return_type_for(schema)
    assert _return_type_for(schema) != _wrapper_return_type(schema)


def test_no_wrapper_on_disk_excludes_the_error_dict():
    """The regression guard, and it holds in any environment.

    Asserting that every wrapper matches what the generator would emit does
    not hold here -- `build_tools` only writes wrappers for tools that LOAD,
    which depends on the optional dependencies installed. This invariant is
    weaker and environment-independent: whatever a wrapper's annotation is, a
    dict has to satisfy it.
    """
    offenders = []
    for path in sorted(TOOLS.glob("*.py")):
        if path.name.startswith("_"):
            continue
        match = SIGNATURE.search(path.read_text("utf-8"))
        if not match:
            continue
        annotation = match.group(1)
        if annotation != "Any" and "dict[str, Any]" not in annotation:
            offenders.append(f"{path.stem}: {annotation}")

    assert not offenders, (
        f"{len(offenders)} wrapper(s) annotate a type the framework's error "
        f"dict does not satisfy: {offenders[:10]}"
    )


def test_the_signature_and_the_docstring_agree():
    """Both come from the same generated value, so a rewrite must move both."""
    returns = re.compile(r"\n    Returns\n    -------\n    (.+)\n")
    disagreeing = []
    for path in sorted(TOOLS.glob("*.py")):
        if path.name.startswith("_"):
            continue
        source = path.read_text("utf-8")
        sig, doc = SIGNATURE.search(source), returns.search(source)
        if not sig or not doc:
            continue
        if sig.group(1) != doc.group(1):
            disagreeing.append(f"{path.stem}: {sig.group(1)} vs {doc.group(1)}")

    assert not disagreeing, disagreeing[:10]


def test_the_framework_really_does_answer_a_dict_on_failure():
    """The premise of the whole change, asserted rather than assumed."""
    from tooluniverse import ToolUniverse

    tu = ToolUniverse()
    tu.load_tools(include_tools=["ClinGen_dosage_region_search"])

    unknown = tu.run_one_function({"name": "definitely_not_a_tool", "arguments": {}})
    assert isinstance(unknown, dict)
    assert unknown.get("status") == "error"

    # a declared-array tool reached with an invalid parameter: still a dict
    bad_params = tu.run_one_function(
        {"name": "ClinGen_dosage_region_search", "arguments": {"chromosome": 123}}
    )
    assert isinstance(bad_params, dict)
    assert bad_params.get("status") == "error"
