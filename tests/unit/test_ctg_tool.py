"""Unit tests for ClinicalTrialsTool search-param translation.

The tool sits on CT.gov's v2 API, which has no `filter.studyType` (and no
`filter.phase`) — both filters must be expressed via `filter.advanced`
AREA clauses. These tests pin the outgoing URL shape so a future refactor
can't silently regress the AREA-clause construction.
"""

from unittest.mock import Mock, patch

import pytest

from tooluniverse.ctg_tool import ClinicalTrialsTool


def make_search_tool():
    """Construct a search-operation ClinicalTrialsTool with minimal config."""
    return ClinicalTrialsTool(
        {
            "name": "ClinicalTrials_search_studies",
            "type": "ClinicalTrialsTool",
            "fields": {"operation": "search"},
            "query_schema": {},
            "parameter": {"type": "object", "properties": {}},
        }
    )


def make_empty_studies_response():
    response = Mock()
    response.status_code = 200
    response.raise_for_status.return_value = None
    response.json.return_value = {"studies": [], "totalCount": 0}
    return response


@pytest.mark.unit
@patch("requests.get")
def test_filter_study_type_builds_area_clause(mock_get):
    """filter_study_type must NOT appear as a query param; it must go into filter.advanced as AREA[StudyType]<value>."""
    mock_get.return_value = make_empty_studies_response()

    make_search_tool().run(
        {"query_cond": "asthma", "filter_study_type": "INTERVENTIONAL"}
    )

    params = mock_get.call_args.kwargs["params"]
    assert "filter.studyType" not in params, (
        "Regression: CT.gov v2 has no filter.studyType param; passing it 400s."
    )
    assert params["filter.advanced"] == "AREA[StudyType]INTERVENTIONAL"


@pytest.mark.unit
@patch("requests.get")
def test_filter_study_type_multi_value_uses_or_with_parens(mock_get):
    """Comma-separated study types must join with OR inside parentheses."""
    mock_get.return_value = make_empty_studies_response()

    make_search_tool().run(
        {"query_cond": "asthma", "filter_study_type": "INTERVENTIONAL,OBSERVATIONAL"}
    )

    advanced = mock_get.call_args.kwargs["params"]["filter.advanced"]
    assert advanced == (
        "(AREA[StudyType]INTERVENTIONAL OR AREA[StudyType]OBSERVATIONAL)"
    )


@pytest.mark.unit
@patch("requests.get")
def test_filter_study_type_combines_with_filter_phase_via_and(mock_get):
    """Study-type and phase clauses must combine with AND in filter.advanced (no regression on phase handling)."""
    mock_get.return_value = make_empty_studies_response()

    make_search_tool().run(
        {
            "query_cond": "asthma",
            "filter_study_type": "INTERVENTIONAL",
            "filter_phase": "PHASE3",
        }
    )

    advanced = mock_get.call_args.kwargs["params"]["filter.advanced"]
    # Order of clauses matches argument-dict iteration order (insertion-preserving in py3.7+);
    # accept either ordering so the test isn't brittle to caller key order.
    assert advanced in (
        "AREA[Phase]PHASE3 AND AREA[StudyType]INTERVENTIONAL",
        "AREA[StudyType]INTERVENTIONAL AND AREA[Phase]PHASE3",
    )
