"""Regression guards for GDCMutationFreqByProjectTool numerator/denominator.

Fix-R4A-002: the GDC analysis endpoint's nested `case_summary.doc_count` is
NOT a project's total case count -- confirmed against the raw API and
cross-checked with GDC_search_cases/GDC_list_projects (e.g. it reported 2282
for TCGA-COAD when the real total is 461). The fix looks up true per-project
totals via the /projects endpoint's `summary.case_count` field, same as
GDC_list_projects already does.

Fix-Round3-001: the analysis endpoint's bucket `doc_count` (the numerator)
counts SSM-*occurrence* records, not distinct cases, so a case with more
than one sequenced sample/aliquot is counted once per occurrence -- for
gene_symbol=KRAS in project TCGA-TGCT this reported mutated=255/total=263
(97%) when only 13 cases (~5%) actually carry a KRAS mutation. The fix
derives mutated_case_count by paginating raw `/ssm_occurrences` records and
counting distinct `case.case_id` values per project instead.
"""

from unittest.mock import patch

import pytest

from tooluniverse.gdc_tool import GDCMutationFreqByProjectTool

pytestmark = pytest.mark.unit

_OCCURRENCES_RESPONSE = {
    "data": {
        "hits": [
            {"case": {"case_id": "case-1", "project": {"project_id": "TCGA-COAD"}}},
            {"case": {"case_id": "case-2", "project": {"project_id": "TCGA-COAD"}}},
            # Same case with a second distinct SSM occurrence record -- must
            # not be double-counted as two mutated cases.
            {"case": {"case_id": "case-2", "project": {"project_id": "TCGA-COAD"}}},
        ],
        "pagination": {"total": 3},
    }
}

_PROJECTS_RESPONSE = {
    "data": {
        "hits": [
            {"project_id": "TCGA-COAD", "summary": {"case_count": 461}},
        ]
    }
}


def test_numerator_is_distinct_cases_not_occurrence_records():
    """mutated_case_count must dedupe by case_id, not count raw occurrence
    rows (case-2 appears twice above but should only count once)."""
    tool = GDCMutationFreqByProjectTool({})

    with patch(
        "tooluniverse.gdc_tool._http_get",
        side_effect=[_OCCURRENCES_RESPONSE, _PROJECTS_RESPONSE],
    ):
        result = tool.run({"gene_symbol": "KRAS"})

    assert result["status"] == "success"
    project = result["data"]["projects"][0]
    assert project["project_id"] == "TCGA-COAD"
    assert project["mutated_case_count"] == 2  # case-1, case-2 (deduped)
    assert project["total_case_count"] == 461
    assert project["frequency"] == round(2 / 461, 4)


def test_project_dropped_if_true_total_lookup_fails():
    """If the /projects lookup errors, we have no reliable denominator for
    that project, so it must be dropped rather than shown with a wrong or
    fabricated total (e.g. the buggy case_summary.doc_count field, which no
    longer exists in the /ssm_occurrences-based response at all)."""
    tool = GDCMutationFreqByProjectTool({})

    with patch(
        "tooluniverse.gdc_tool._http_get",
        side_effect=[_OCCURRENCES_RESPONSE, Exception("network error")],
    ):
        result = tool.run({"gene_symbol": "KRAS"})

    assert result["status"] == "success"
    assert result["data"]["projects"] == []
    assert result["data"]["project_count"] == 0
