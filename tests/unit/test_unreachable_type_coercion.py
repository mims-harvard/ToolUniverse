"""Coercion code is dead unless the schema permits the type it converts.

Each tool below already converted one input form to the other, but declared a
type that made validation reject that form before `run()` was entered — the
same defect as #611 and #613. These assertions pin the schema side, which is
what keeps the conversion reachable.
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

DATA = Path(__file__).resolve().parents[2] / "src/tooluniverse/data"

# (tool name, parameter) -> both forms must be accepted
CASES = [
    ("GBIF_parse_name", "names"),
    ("PathwayCommons_paths_between", "genes"),
    ("STITCH_get_interaction_partners", "identifiers"),
    ("STITCH_get_chemical_protein_interactions", "identifiers"),
    ("SwissModel_get_models_batch", "uniprot_ids"),
    ("DGIdb_get_drug_gene_interactions", "interaction_types"),
    ("list_tools", "fields"),
    ("ReactomeAnalysis_pathway_enrichment", "identifiers"),
    ("ReactomeAnalysis_species_comparison", "identifiers"),
    ("ReactomeAnalysis_expression_analysis", "identifiers"),
    ("iDigBio_summary_facets", "top_fields"),
]


def _all_tools():
    tools = {}
    for path in DATA.glob("*.json"):
        try:
            loaded = json.loads(path.read_text())
        except Exception:
            continue
        entries = loaded if isinstance(loaded, list) else loaded.get("tools", [])
        if not isinstance(entries, list):
            continue
        for tool in entries:
            if isinstance(tool, dict) and tool.get("name"):
                tools[tool["name"]] = tool
    return tools


@pytest.mark.parametrize(("tool_name", "param"), CASES)
def test_both_forms_are_accepted(tool_name, param):
    tool = _all_tools().get(tool_name)
    assert tool is not None, f"{tool_name} is not registered"
    schema = (tool["parameter"]["properties"] or {})[param]
    declared = schema["type"]
    declared = {declared} if isinstance(declared, str) else set(declared)
    assert "array" in declared, f"{tool_name}.{param} rejects a list"
    assert "string" in declared, f"{tool_name}.{param} rejects a string"
