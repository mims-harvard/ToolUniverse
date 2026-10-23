"""Round 221: SAbDab arguments the tool cannot honour must not be dropped."""

from unittest.mock import patch

import pytest

from tooluniverse.sabdab_tool import SAbDabTool

pytestmark = pytest.mark.unit


def _tool(operation):
    return SAbDabTool(
        {
            "parameter": {
                "properties": {"operation": {"type": "string", "const": operation}}
            }
        }
    )


def test_unknown_parameter_is_not_silently_ignored():
    """A misspelled filter must fail instead of broadening the search."""
    with patch("tooluniverse.sabdab_tool.requests.get") as get:
        result = _tool("search_structures").run({"resoultion_max": 2.0})
    get.assert_not_called()
    assert result["status"] == "error"
    assert "resoultion_max" in result["error"]


@pytest.mark.parametrize(
    ("operation", "arguments"),
    [
        ("get_structure", {"pdb_id": "3hfm", "chain": "H"}),
        ("get_structure_summary", {"pdb_id": "3hfm", "species": "human"}),
        ("get_summary", {"species": "human"}),
    ],
)
def test_unknown_parameter_is_rejected_for_every_operation(operation, arguments):
    with patch("tooluniverse.sabdab_tool.requests.get") as get:
        result = _tool(operation).run(arguments)
    get.assert_not_called()
    assert result["status"] == "error"
    assert "Unknown parameter" in result["error"]
