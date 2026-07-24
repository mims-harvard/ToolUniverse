"""OpenTargets drug query must not request fields removed from the schema.

Regression: OpenTargets removed `yearOfFirstApproval` from the Drug type and
renamed `maximumClinicalTrialPhase` -> `maximumClinicalStage`. The
OpenTargets_get_drug_description_by_chemblId query still requested the old
names, so every call returned HTTP 400 "Cannot query field ...". The query must
use only current fields.
"""

import json
import os

import pytest

pytestmark = pytest.mark.unit

_CONFIG = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "src",
    "tooluniverse",
    "data",
    "opentarget_tools.json",
)


def _tool(name):
    with open(_CONFIG) as fh:
        for t in json.load(fh):
            if isinstance(t, dict) and t.get("name") == name:
                return t
    raise AssertionError(f"{name} not found in opentarget_tools.json")


def test_drug_description_query_uses_current_fields():
    tool = _tool("OpenTargets_get_drug_description_by_chemblId")
    query = tool.get("query_schema", "")
    # removed / renamed fields must be gone from the GraphQL query
    assert "yearOfFirstApproval" not in query
    assert "maximumClinicalTrialPhase" not in query
    # the current replacement field must be present
    assert "maximumClinicalStage" in query


def test_drug_description_has_real_example():
    tool = _tool("OpenTargets_get_drug_description_by_chemblId")
    examples = tool.get("test_examples", [])
    assert examples and examples[0].get("chemblId")


# Every removed/renamed field must be absent from the corresponding query, and the
# current replacement must be present. (OpenTargets GraphQL schema drift, Round 014.)
_STALE_TO_CURRENT = {
    "OpenTargets_get_drug_blackbox_status_by_chembl_ID": ("blackBoxWarning", "drugWarnings"),
    "OpenTargets_get_approved_indications_by_drug_chemblId": ("approvedIndications", "indications"),
    "OpenTargets_get_gene_ontology_terms_by_goID": ("\n          name\n", "label"),
    "OpenTargets_get_target_gene_ontology_by_ensemblID": ("\n              name\n", "label"),
}


@pytest.mark.parametrize("name,fields", list(_STALE_TO_CURRENT.items()))
def test_opentargets_queries_use_current_schema(name, fields):
    stale, current = fields
    query = _tool(name).get("query_schema", "")
    assert stale not in query, f"{name} still queries removed field {stale!r}"
    assert current in query, f"{name} missing current field {current!r}"
    assert _tool(name).get("test_examples"), f"{name} has no test_example"


def test_new_target_info_tool_is_well_formed():
    # New tool built to fill the audit gap (OpenTargets_get_target had no
    # generic target-info tool). Query must use only current Target fields.
    tool = _tool("OpenTargets_get_target_info_by_ensemblID")
    query = tool.get("query_schema", "")
    for field in ("approvedSymbol", "biotype", "functionDescriptions", "genomicLocation"):
        assert field in query, f"target-info query missing {field!r}"
    assert tool.get("type") == "OpenTarget"
    assert tool["test_examples"][0]["ensemblId"].startswith("ENSG")
    # return_schema is the standard success/error oneOf
    assert "oneOf" in tool.get("return_schema", {})


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
