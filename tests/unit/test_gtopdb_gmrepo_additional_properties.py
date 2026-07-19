"""Regression guard for Fix-R29-2/3: GtoPdb_search_diseases and
GMrepo_get_phenotypes silently ignored unrecognized filter parameters
instead of rejecting them. Confirmed live:
  - GtoPdb_search_diseases({"disease_name": "Crohn"}) returned 50
    completely unrelated diseases (Myasthenic syndrome, Deafness, etc.)
    with status: success and no indication "disease_name" was ignored
    (the correct param is "name" or its alias "query").
  - GMrepo_get_phenotypes({"keyword": "Crohn"}) returned the default
    unfiltered top-20 phenotype list with status: success -- and the
    tool's own description text ("Optionally filter by keyword...")
    directly primed the wrong param name; the correct param is "query".
Both tool classes extend BaseTool, whose validate_parameters() already
enforces additionalProperties: false via jsonschema once declared; the
schemas previously omitted that flag entirely. Fixed with config-only
changes (no Python code touched), plus a description-wording fix for
GMrepo_get_phenotypes so it no longer suggests a nonexistent "keyword" arg.
"""

import json
from pathlib import Path

import pytest

from tooluniverse.gmrepo_tool import GmrepoTool
from tooluniverse.gtopdb_tool import GtoPdbRESTTool

pytestmark = pytest.mark.unit

_DATA_DIR = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data"


def _load_tool_config(filename, tool_name):
    configs = json.loads((_DATA_DIR / filename).read_text())
    for cfg in configs:
        if cfg["name"] == tool_name:
            return cfg
    raise AssertionError(f"{tool_name} not found in {filename}")


class TestGtoPdbSearchDiseasesValidation:
    def test_schema_declares_additional_properties_false(self):
        cfg = _load_tool_config("gtopdb_tools.json", "GtoPdb_search_diseases")
        assert cfg["parameter"]["additionalProperties"] is False

    def test_unrecognized_param_is_rejected(self):
        tool = GtoPdbRESTTool(_load_tool_config("gtopdb_tools.json", "GtoPdb_search_diseases"))
        error = tool.validate_parameters({"disease_name": "Crohn"})
        assert error is not None
        assert "disease_name" in str(error)

    def test_documented_params_are_accepted(self):
        tool = GtoPdbRESTTool(_load_tool_config("gtopdb_tools.json", "GtoPdb_search_diseases"))
        assert tool.validate_parameters({"name": "Crohn"}) is None
        assert tool.validate_parameters({"query": "Crohn"}) is None


class TestGMrepoGetPhenotypesValidation:
    def test_schema_declares_additional_properties_false(self):
        cfg = _load_tool_config("gmrepo_tools.json", "GMrepo_get_phenotypes")
        assert cfg["parameter"]["additionalProperties"] is False

    def test_unrecognized_param_is_rejected(self):
        tool = GmrepoTool(_load_tool_config("gmrepo_tools.json", "GMrepo_get_phenotypes"))
        error = tool.validate_parameters({"keyword": "Crohn"})
        assert error is not None
        assert "keyword" in str(error)

    def test_documented_param_is_accepted(self):
        tool = GmrepoTool(_load_tool_config("gmrepo_tools.json", "GMrepo_get_phenotypes"))
        assert tool.validate_parameters({"query": "Crohn"}) is None

    def test_description_no_longer_suggests_wrong_param_name(self):
        cfg = _load_tool_config("gmrepo_tools.json", "GMrepo_get_phenotypes")
        assert "keyword" not in cfg["description"]
