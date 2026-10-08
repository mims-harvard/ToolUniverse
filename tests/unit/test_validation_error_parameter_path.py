"""Regression guard: a validation error names the argument the caller passed.

`BaseTool.validate_parameters` used only the last element of the jsonschema
path, so a bad element inside an array was reported as a parameter named
after its index. `DoseResponse_calculate_ic50` with responses
`[2, 10, 48, 88, "n/a"]` answered "Parameter validation failed for '4'", and
`details["parameter"]` was "4". A nested key lost its parent the same way.
"""

import pytest

from tooluniverse.base_tool import BaseTool
from tooluniverse.exceptions import ToolValidationError

pytestmark = pytest.mark.unit

NUMBERS = {"type": "array", "items": {"type": "number"}}

TOOL = BaseTool(
    {
        "name": "path_tool",
        "type": "PathTool",
        "description": "Schema with array, nested and anyOf parameters.",
        "parameter": {
            "type": "object",
            "properties": {
                "concentrations": NUMBERS,
                "responses": NUMBERS,
                "options": {
                    "type": "object",
                    "properties": {"mode": {"type": "string", "enum": ["a", "b"]}},
                },
                "weights": {"anyOf": [NUMBERS, {"type": "null"}]},
                "limit": {"type": "integer"},
            },
            "required": ["concentrations"],
        },
    }
)


@pytest.mark.parametrize(
    "arguments,rendered,parameter,path",
    [
        (
            {"concentrations": [1, 2], "responses": [2, 10, 48, 88, "n/a"]},
            "responses[4]",
            "responses",
            ["responses", 4],
        ),
        (
            {"concentrations": [0.001, 0.01, None, 1, 10]},
            "concentrations[2]",
            "concentrations",
            ["concentrations", 2],
        ),
        (
            {"concentrations": [1], "options": {"mode": "c"}},
            "options.mode",
            "options",
            ["options", "mode"],
        ),
        # Under anyOf jsonschema reports a sub-error whose relative `path`
        # starts at the index, so only `absolute_path` still has the name.
        (
            {"concentrations": [1], "weights": [1, "heavy"]},
            "weights[1]",
            "weights",
            ["weights", 1],
        ),
    ],
)
def test_error_names_the_argument(arguments, rendered, parameter, path):
    error = TOOL.validate_parameters(arguments)

    assert isinstance(error, ToolValidationError)
    assert str(error).startswith(f"Parameter validation failed for '{rendered}': ")
    assert error.details["parameter"] == parameter
    assert error.details["path"] == path


def test_top_level_and_root_errors_are_unchanged():
    scalar = TOOL.validate_parameters({"concentrations": [1], "limit": "ten"})
    assert str(scalar).startswith("Parameter validation failed for 'limit': ")
    assert scalar.details["parameter"] == "limit"

    missing = TOOL.validate_parameters({"responses": [1]})
    assert str(missing).startswith("Parameter validation failed for 'root': ")
    assert missing.details["parameter"] == "root"
    assert missing.details["path"] == []
