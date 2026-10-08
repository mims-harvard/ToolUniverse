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


# GtoPdb_search_diseases, the tool this guard was written against, is retired:
# GtoPdb's REST service is key-gated and publishes no open disease file, so it
# moved to data/broken_apis/gtopdb_rest.json. The invariant outlived it, and
# checking it found that the original fix never reached the siblings -- all four
# surviving tools omitted additionalProperties, so each still accepted a
# misspelled filter and answered as though it had filtered.
GTOPDB_TOOLS = {
    "GtoPdb_search_targets": ({"target_name": "EGFR"}, {"name": "EGFR"}),
    "GtoPdb_search_ligands": ({"ligand_name": "aspirin"}, {"name": "aspirin"}),
    "GtoPdb_get_interactions": ({"gene": "KRAS"}, {"gene_symbol": "KRAS"}),
    "GtoPdb_get_ligand_properties": ({"id": 4139}, {"ligand_id": 4139}),
}


class TestGtoPdbParameterValidation:
    @pytest.mark.parametrize("tool_name", sorted(GTOPDB_TOOLS))
    def test_schema_declares_additional_properties_false(self, tool_name):
        cfg = _load_tool_config("gtopdb_tools.json", tool_name)
        assert cfg["parameter"]["additionalProperties"] is False

    @pytest.mark.parametrize("tool_name", sorted(GTOPDB_TOOLS))
    def test_unrecognized_param_is_rejected(self, tool_name):
        misspelled, _ = GTOPDB_TOOLS[tool_name]
        tool = GtoPdbRESTTool(_load_tool_config("gtopdb_tools.json", tool_name))

        error = tool.validate_parameters(misspelled)

        assert error is not None, (
            f"{tool_name} accepted {misspelled} and would answer as though it "
            "had filtered on it"
        )
        assert next(iter(misspelled)) in str(error)

    @pytest.mark.parametrize("tool_name", sorted(GTOPDB_TOOLS))
    def test_documented_params_are_accepted(self, tool_name):
        _, documented = GTOPDB_TOOLS[tool_name]
        tool = GtoPdbRESTTool(_load_tool_config("gtopdb_tools.json", tool_name))

        assert tool.validate_parameters(documented) is None


def test_the_retired_disease_tool_is_gone():
    configs = json.loads((_DATA_DIR / "gtopdb_tools.json").read_text())
    assert "GtoPdb_search_diseases" not in {cfg["name"] for cfg in configs}


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
