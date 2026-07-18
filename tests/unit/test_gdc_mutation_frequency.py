"""Regression guard for Fix-R4A-002: GDCMutationFreqByProjectTool denominator.

The GDC analysis endpoint's nested `case_summary.doc_count` is NOT a
project's total case count -- confirmed against the raw API and
cross-checked with GDC_search_cases/GDC_list_projects (e.g. it reported
2282 for TCGA-COAD when the real total is 461, understating KRAS mutation
frequency in colorectal cancer by ~5x: 11% instead of the real ~54%).
The fix looks up true per-project totals via the /projects endpoint's
`summary.case_count` field, same as GDC_list_projects already does.
"""

from unittest.mock import patch

import pytest

from tooluniverse.gdc_tool import GDCMutationFreqByProjectTool

pytestmark = pytest.mark.unit

_ANALYSIS_RESPONSE = {
    "aggregations": {
        "projects": {
            "buckets": [
                {
                    "key": "TCGA-COAD",
                    "doc_count": 250,
                    "case_summary": {
                        "doc_count": 2282,  # wrong: not a real case total
                        "case_with_ssm": {"doc_count": 250},
                    },
                }
            ]
        }
    }
}

_PROJECTS_RESPONSE = {
    "data": {
        "hits": [
            {"project_id": "TCGA-COAD", "summary": {"case_count": 461}},
        ]
    }
}


def test_uses_projects_endpoint_case_count_not_case_summary():
    tool = GDCMutationFreqByProjectTool({})

    with patch(
        "tooluniverse.gdc_tool._http_get",
        side_effect=[_ANALYSIS_RESPONSE, _PROJECTS_RESPONSE],
    ):
        result = tool.run({"gene_symbol": "KRAS"})

    assert result["status"] == "success"
    project = result["data"]["projects"][0]
    assert project["project_id"] == "TCGA-COAD"
    assert project["mutated_case_count"] == 250
    assert project["total_case_count"] == 461
    assert project["frequency"] == round(250 / 461, 4)


def test_falls_back_to_case_summary_if_projects_lookup_fails():
    """If the /projects lookup errors, still return a (less reliable)
    result rather than failing the whole call."""
    tool = GDCMutationFreqByProjectTool({})

    with patch(
        "tooluniverse.gdc_tool._http_get",
        side_effect=[_ANALYSIS_RESPONSE, Exception("network error")],
    ):
        result = tool.run({"gene_symbol": "KRAS"})

    assert result["status"] == "success"
    project = result["data"]["projects"][0]
    assert project["total_case_count"] == 2282  # fallback value
