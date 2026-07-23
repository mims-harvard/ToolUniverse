"""Unit test for the CIViC evidence-item `significance` filter.

Regression: `civic_search_evidence_items` advertised `significance` as a
supported filter (it is whitelisted in the tool's known-parameter set and named
in the "Supported filters" error text), but the GraphQL query template bound
`$evidenceType` only — `significance` appeared solely as a *returned field*, so
passing `significance="RESISTANCE"` was silently ignored and the tool returned
an unfiltered, significance-mixed evidence dump. That is clinically dangerous:
an oncologist filtering for RESISTANCE evidence would receive SENSITIVITY items
mixed in. The fix adds `$significance: EvidenceSignificance` to the query
signature and the `evidenceItems(...)` argument list so the filter is honored.
"""
import glob
import json

import pytest

from tooluniverse.civic_tool import CIViCTool


def _load_config(name):
    for f in glob.glob("src/tooluniverse/data/*.json"):
        try:
            data = json.load(open(f))
        except ValueError:
            continue
        if not isinstance(data, list):
            continue
        for tool in data:
            if isinstance(tool, dict) and tool.get("name") == name:
                return tool
    raise AssertionError(f"tool config not found: {name}")


@pytest.mark.unit
def test_significance_is_bound_in_query_template():
    """The GraphQL query must declare and USE $significance as a filter arg."""
    cfg = _load_config("civic_search_evidence_items")
    query = cfg["fields"]["query"]
    # Declared as a typed variable...
    assert "$significance: EvidenceSignificance" in query
    # ...and actually passed to the evidenceItems() filter (not just returned).
    assert "significance: $significance" in query


@pytest.mark.unit
def test_significance_is_a_declared_parameter():
    """significance must be discoverable in `tu info`, not just functional."""
    cfg = _load_config("civic_search_evidence_items")
    props = cfg["parameter"]["properties"]
    assert "significance" in props
    assert "RESISTANCE" in props["significance"]["description"]


@pytest.mark.unit
def test_build_graphql_query_binds_significance():
    """A user-supplied significance value must reach the GraphQL variables."""
    cfg = _load_config("civic_search_evidence_items")
    tool = CIViCTool(cfg)
    payload = tool._build_graphql_query(
        {"molecular_profile": "KRAS G12C", "significance": "RESISTANCE", "limit": 50}
    )
    assert payload["variables"].get("significance") == "RESISTANCE"
    # sanity: the sibling evidence_type mapping still works alongside it
    payload2 = tool._build_graphql_query({"evidence_type": "PROGNOSTIC"})
    assert payload2["variables"].get("evidenceType") == "PROGNOSTIC"
