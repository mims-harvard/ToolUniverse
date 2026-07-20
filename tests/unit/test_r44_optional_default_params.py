"""Regression guard for Fix-R44A-1: four more round-37-backlog tools wrongly
required params that already have a working Python-level default:

- Fatcat_search_scholar's `max_results` (fatcat_tool.py already does
  `int(arguments.get("max_results", 10))`).
- OpenAIRE_search_publications' `max_results` and `type` (openaire_tool.py
  already does `int(arguments.get("max_results", 10))` and
  `arguments.get("type", "publications")`, a valid enum value that maps to
  a real endpoint via `_endpoint_for_type`).
- NeuroMorpho_get_field_values' `field_name` (neuromorpho_tool.py already
  does `arguments.get("field_name", "species")`).
- TRIP_Database_Guidelines_Search's `search_type` (unified_guideline_tools.py
  already does `arguments.get("search_type", "guideline")`).

Confirmed live for all four: omitting the param previously failed schema
validation despite the tool being fully answerable without it.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.fatcat_tool import FatcatScholarTool
from tooluniverse.openaire_tool import OpenAIRETool
from tooluniverse.neuromorpho_tool import NeuroMorphoTool
from tooluniverse.unified_guideline_tools import TRIPDatabaseTool

pytestmark = pytest.mark.unit

_DATA_DIR = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data"


def _tool_config(filename, name):
    configs = json.loads((_DATA_DIR / filename).read_text())
    for cfg in configs:
        if cfg["name"] == name:
            return cfg
    raise AssertionError(f"{name} not found in {filename}")


def test_fatcat_requires_only_query():
    cfg = _tool_config("fatcat_tools.json", "Fatcat_search_scholar")
    assert cfg["parameter"]["required"] == ["query"]


def test_openaire_requires_only_query():
    cfg = _tool_config("openaire_tools.json", "OpenAIRE_search_publications")
    assert cfg["parameter"]["required"] == ["query"]


def test_neuromorpho_field_values_requires_nothing():
    cfg = _tool_config("neuromorpho_tools.json", "NeuroMorpho_get_field_values")
    assert cfg["parameter"]["required"] == []


def test_trip_requires_only_query():
    cfg = _tool_config("unified_guideline_tools.json", "TRIP_Database_Guidelines_Search")
    assert cfg["parameter"]["required"] == ["query"]


def test_fatcat_run_uses_default_max_results_when_omitted():
    cfg = _tool_config("fatcat_tools.json", "Fatcat_search_scholar")
    tool = FatcatScholarTool(cfg)

    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"estimate": {"total": 0}, "results": []}

    with patch("tooluniverse.fatcat_tool.requests.get", return_value=resp) as mock_get:
        tool.run({"query": "CRISPR"})
        params = mock_get.call_args.kwargs["params"]

    assert params["limit"] == 10


def test_openaire_run_uses_defaults_when_omitted():
    cfg = _tool_config("openaire_tools.json", "OpenAIRE_search_publications")
    tool = OpenAIRETool(cfg)

    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"response": {"results": {}}}

    with patch("tooluniverse.openaire_tool.requests.get", return_value=resp) as mock_get:
        result = tool.run({"query": "CRISPR"})
        endpoint = mock_get.call_args.args[0]
        params = mock_get.call_args.kwargs["params"]

    assert endpoint == "https://api.openaire.eu/search/publications"
    assert params["size"] == 10
    assert result["data"]["type"] == "publications"


def test_neuromorpho_field_values_run_uses_default_field_name_when_omitted():
    cfg = _tool_config("neuromorpho_tools.json", "NeuroMorpho_get_field_values")
    tool = NeuroMorphoTool(cfg)

    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"fields": ["mouse", "rat"], "page": {}}

    with patch(
        "tooluniverse.neuromorpho_tool.requests.get", return_value=resp
    ) as mock_get:
        tool.run({})
        called_url = mock_get.call_args.args[0]

    assert called_url.endswith("/neuron/fields/species")


def test_trip_run_uses_default_search_type_when_omitted():
    cfg = _tool_config("unified_guideline_tools.json", "TRIP_Database_Guidelines_Search")
    tool = TRIPDatabaseTool(cfg)

    resp = MagicMock()
    resp.status_code = 200
    resp.content = b"<results><total>0</total><count>0</count></results>"
    resp.raise_for_status.return_value = None

    with patch.object(tool.session, "get", return_value=resp) as mock_get:
        tool.run({"query": "diabetes management"})
        params = mock_get.call_args.kwargs["params"]

    assert params["searchType"] == "guideline"
