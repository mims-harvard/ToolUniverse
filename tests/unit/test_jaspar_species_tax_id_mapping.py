"""Regression test: jaspar_search_matrices must send its species filter as `tax_id`.

JASPAR names the taxonomy filter ``tax_id``; the tool declared it as ``species``
and forwarded that name verbatim. JASPAR ignores unrecognised query parameters
rather than rejecting them, so the filter was dropped and the *unfiltered* result
set came back as a success:

    species=9606     -> count 215   (all species)
    species=9999999  -> count 215   (identical: proof the filter was ignored)

After the fix the same queries return 156 and 0 respectively.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tooluniverse.jaspar_tool import JASPARRESTTool


CONFIG_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "tooluniverse"
    / "data"
    / "jaspar_tools.json"
)
CONFIGS = {t["name"]: t for t in json.loads(CONFIG_PATH.read_text())}


def _tool_with_capture(name):
    tool = JASPARRESTTool(dict(CONFIGS[name]))
    captured = {}

    def get(url, params=None, timeout=None):
        captured["url"] = url
        captured["params"] = params or {}
        response = MagicMock()
        response.status_code = 200
        response.url = url
        response.json.return_value = {"count": 0, "results": []}
        response.raise_for_status.return_value = None
        return response

    session = MagicMock()
    session.get.side_effect = get
    tool.session = session
    return tool, captured


def test_species_is_sent_as_tax_id():
    tool, captured = _tool_with_capture("jaspar_search_matrices")
    result = tool.run({"search": "FOX", "species": "9606", "page_size": 5})
    assert result["status"] == "success"
    assert captured["params"].get("tax_id") == "9606"
    assert "species" not in captured["params"], (
        "JASPAR ignores unknown params, so a leftover `species` key silently "
        "drops the taxonomy filter"
    )


def test_other_filters_keep_their_names():
    tool, captured = _tool_with_capture("jaspar_search_matrices")
    tool.run(
        {
            "search": "FOX",
            "name": "FOXA1",
            "collection": "CORE",
            "tax_group": "vertebrates",
            "page": 2,
            "page_size": 5,
        }
    )
    params = captured["params"]
    assert params["search"] == "FOX"
    assert params["name"] == "FOXA1"
    assert params["collection"] == "CORE"
    assert params["tax_group"] == "vertebrates"
    assert params["page"] == 2
    assert params["page_size"] == 5


def test_config_declares_the_param_map():
    fields = CONFIGS["jaspar_search_matrices"]["fields"]
    assert fields.get("param_map", {}).get("species") == "tax_id"


def test_config_description_records_the_upstream_name():
    prop = CONFIGS["jaspar_search_matrices"]["parameter"]["properties"]["species"]
    assert "tax_id" in prop["description"]


def test_path_placeholders_still_resolve_before_mapping():
    tool, captured = _tool_with_capture("jaspar_get_matrix_versions")
    tool.run({"base_id": "MA0002", "page_size": 5})
    assert "MA0002" in captured["url"]
    assert "base_id" not in captured["params"]
    assert captured["params"]["page_size"] == 5


def test_tools_without_a_param_map_are_unchanged():
    tool, captured = _tool_with_capture("JASPAR_get_transcription_factors")
    tool.run({"collection": "CORE", "page_size": 3})
    assert captured["params"] == {"collection": "CORE", "page_size": 3}


def test_none_valued_arguments_are_dropped():
    tool, captured = _tool_with_capture("jaspar_search_matrices")
    tool.run({"search": "FOX", "species": None})
    assert "tax_id" not in captured["params"]
    assert "species" not in captured["params"]


def test_non_param_mode_tool_still_uses_path_substitution():
    tool, captured = _tool_with_capture("jaspar_get_matrix")
    result = tool.run({"matrix_id": "MA0002.1"})
    assert result["status"] == "success"
    assert captured["url"].endswith("MA0002.1")


def test_upstream_error_is_reported_not_raised():
    tool = JASPARRESTTool(dict(CONFIGS["jaspar_search_matrices"]))
    session = MagicMock()
    session.get.side_effect = RuntimeError("boom")
    tool.session = session
    result = tool.run({"search": "FOX"})
    assert result["status"] == "error"
    assert "JASPAR API error" in result["error"]


@pytest.mark.parametrize(
    "name", ["jaspar_search_matrices", "JASPAR_get_transcription_factors"]
)
def test_configs_remain_valid_json_schema_shape(name):
    cfg = CONFIGS[name]
    assert cfg["fields"]["use_params"] is True
    assert "properties" in cfg["parameter"]
