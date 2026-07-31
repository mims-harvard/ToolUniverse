"""Regression guard for OpenTargets_get_known_drugs_by_drug_chemblId.

The tool is named "get_known_drugs" and its description promises "known drugs and
associated information", but its GraphQL query fetched only bare drug metadata
(id/name/maximumClinicalStage/drugType/drugWarnings) -- no indications, no
mechanisms of action, no targets. (The `knownDrugs` field does not exist on the
OpenTargets `Drug` type; the meaningful associated info is `indications` and
`mechanismsOfAction`.) So the tool returned almost nothing useful despite its
name. The query now includes indications (diseases + max clinical phase) and
mechanisms of action (with targets).
"""
import glob
import json

import pytest


def _load(name):
    for f in glob.glob("src/tooluniverse/data/*.json"):
        try:
            data = json.load(open(f))
        except ValueError:
            continue
        if isinstance(data, list):
            for tool in data:
                if isinstance(tool, dict) and tool.get("name") == name:
                    return tool
    raise AssertionError(f"tool config not found: {name}")


@pytest.mark.unit
def test_known_drugs_query_requests_associated_information():
    tool = _load("OpenTargets_get_known_drugs_by_drug_chemblId")
    query = tool["query_schema"]
    # Associated clinical information the tool name/description promise.
    assert "indications" in query
    assert "mechanismsOfAction" in query
    # indications must carry the disease + clinical phase, not just a count.
    assert "disease" in query
    assert "maxClinicalStage" in query
    # mechanisms must carry the molecular targets acted on.
    assert "targets" in query and "approvedSymbol" in query
