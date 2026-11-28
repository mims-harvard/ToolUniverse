import pytest

from tooluniverse import ToolUniverse
from tooluniverse.utils import evaluate_function_call


@pytest.mark.unit
@pytest.mark.parametrize(
    ("parameter_schema", "arguments", "expected"),
    [
        pytest.param(
            {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
            {},
            (False, "Missing required parameters: ['query']"),
            id="top-level-required-missing",
        ),
        pytest.param(
            {
                "type": "object",
                "properties": {
                    "legacy": {"type": "string", "required": True},
                    "query": {"type": "string"},
                },
                "required": ["query"],
            },
            {"legacy": "value"},
            (False, "Missing required parameters: ['query']"),
            id="both-styles-top-level-missing",
        ),
        pytest.param(
            {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": True,
            },
            {},
            (True, "Function call is valid."),
            id="non-list-top-level-required-ignored",
        ),
        pytest.param(
            {
                "type": "object",
                "properties": {"query": {"type": "string", "required": True}},
                "required": ["query"],
            },
            {},
            (False, "Missing required parameters: ['query']"),
            id="same-key-flagged-both-ways",
        ),
    ],
)
def test_evaluate_function_call_required_parameters(
    parameter_schema, arguments, expected
):
    """Required parameters support standard and legacy schema styles."""
    tool_definition = {"name": "demo", "parameter": parameter_schema}
    function_call = {"name": "demo", "arguments": arguments}

    assert evaluate_function_call(tool_definition, function_call) == expected


@pytest.mark.unit
def test_tooluniverse_check_function_call_honors_shipped_required_list():
    """The public validator honors required lists in shipped tool configs."""
    tool_universe = ToolUniverse()
    tool_universe.load_tools(include_tools=["UniProt_get_entry_by_accession"])

    assert tool_universe.check_function_call(
        {"name": "UniProt_get_entry_by_accession", "arguments": {}}
    ) == (False, "Missing required parameters: ['accession']")
