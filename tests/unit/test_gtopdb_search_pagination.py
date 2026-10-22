import inspect
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.gtopdb_tool import GtoPdbRESTTool
from tooluniverse.tools.GtoPdb_search_diseases import GtoPdb_search_diseases
from tooluniverse.tools.GtoPdb_search_ligands import GtoPdb_search_ligands
from tooluniverse.tools.GtoPdb_search_targets import GtoPdb_search_targets


CONFIG = (
    Path(__file__).parents[2]
    / "src"
    / "tooluniverse"
    / "data"
    / "gtopdb_tools.json"
)


def _config(name):
    configs = json.loads(CONFIG.read_text())
    return next(config for config in configs if config["name"] == name)


@pytest.mark.parametrize(
    "tool_name",
    [
        "GtoPdb_search_targets",
        "GtoPdb_search_ligands",
        "GtoPdb_search_diseases",
    ],
)
@patch("tooluniverse.gtopdb_tool.request_with_retry")
def test_search_pages_are_recoverable(mock_request, tool_name):
    response = MagicMock(status_code=200)
    response.json.return_value = [{"id": i, "name": f"Record {i}"} for i in range(7)]
    mock_request.return_value = response

    result = GtoPdbRESTTool(_config(tool_name)).run({"limit": 3, "offset": 3})

    assert [row["id"] for row in result["data"]] == [3, 4, 5]
    assert result["total_available"] == 7
    assert result["returned"] == 3
    assert result["offset"] == 3
    assert result["limit"] == 3
    assert result["has_more"] is True
    assert result["next_offset"] == 6
    assert result["result_set_complete"] is False
    requested_url = mock_request.call_args.args[2]
    assert "offset=" not in requested_url
    assert "limit=" not in requested_url


def test_generated_search_wrappers_expose_pagination_and_gene_symbol():
    target_params = inspect.signature(GtoPdb_search_targets).parameters
    ligand_params = inspect.signature(GtoPdb_search_ligands).parameters
    disease_params = inspect.signature(GtoPdb_search_diseases).parameters

    assert {"gene_symbol", "limit", "offset"} <= set(target_params)
    assert {"limit", "offset"} <= set(ligand_params)
    assert {"limit", "offset"} <= set(disease_params)
    assert target_params["limit"].default == 50
    assert target_params["offset"].default == 0


@pytest.mark.parametrize(
    "tool_name",
    [
        "GtoPdb_search_targets",
        "GtoPdb_search_ligands",
        "GtoPdb_search_diseases",
    ],
)
def test_search_return_schema_matches_runtime_envelope(tool_name):
    success = _config(tool_name)["return_schema"]["oneOf"][0]
    properties = success["properties"]

    assert success["type"] == "object"
    assert properties["data"]["type"] == "array"
    assert {
        "status",
        "data",
        "total_available",
        "offset",
        "limit",
        "has_more",
        "next_offset",
        "result_set_complete",
    } <= set(properties)
