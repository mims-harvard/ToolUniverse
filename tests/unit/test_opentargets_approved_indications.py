"""Unit test: OpenTargets_get_approved_indications returns only APPROVAL-stage.

Regression: the query returns ALL indications with their maxClinicalStage, so the
tool -- despite its 'approved_indications' name -- listed investigational
(PHASE_1/2) diseases alongside approved ones (selpercatinib: 17 rows, only 5
APPROVAL). A clinician trusting the name would treat Phase-2 indications as
approved. It now filters to APPROVAL-stage rows.
"""
import glob
import json
from unittest.mock import patch

import pytest

from tooluniverse.graphql_tool import OpentargetTool


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
def test_only_approval_stage_rows_returned():
    cfg = _load("OpenTargets_get_approved_indications_by_drug_chemblId")
    tool = OpentargetTool(cfg)
    api = {
        "data": {
            "drug": {
                "id": "CHEMBL4559134",
                "name": "SELPERCATINIB",
                "indications": {
                    "count": 4,
                    "rows": [
                        {"maxClinicalStage": "APPROVAL", "disease": {"name": "MTC"}},
                        {"maxClinicalStage": "PHASE_2", "disease": {"name": "PTC"}},
                        {"maxClinicalStage": "APPROVAL", "disease": {"name": "NSCLC"}},
                        {"maxClinicalStage": "EARLY_PHASE_1", "disease": {"name": "X"}},
                    ],
                },
            }
        }
    }
    with patch("tooluniverse.graphql_tool.execute_query", return_value=api):
        result = tool.run({"chemblId": "CHEMBL4559134"})
    ind = result["data"]["drug"]["indications"]
    assert ind["count"] == 2
    assert {r["maxClinicalStage"] for r in ind["rows"]} == {"APPROVAL"}


@pytest.mark.unit
def test_description_no_longer_claims_multiple_drugs():
    desc = _load("OpenTargets_get_approved_indications_by_drug_chemblId")["description"]
    assert "multiple drugs" not in desc
    assert "approved" in desc.lower()
