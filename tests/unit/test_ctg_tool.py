"""Unit tests for ClinicalTrialsTool search-param translation.

The tool sits on CT.gov's v2 API, which has no `filter.studyType` (and no
`filter.phase`) — both filters must be expressed via `filter.advanced`
AREA clauses. These tests pin the outgoing URL shape so a future refactor
can't silently regress the AREA-clause construction.
"""

from unittest.mock import Mock, patch

import pytest

from tooluniverse.ctg_tool import (
    ClinicalTrialsDetailsTool,
    ClinicalTrialsSearchTool,
    ClinicalTrialsTool,
)


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


def make_search_clinical_trials_tool():
    """Construct the actual `search_clinical_trials` tool (type
    ClinicalTrialsSearchTool), whose run() has its own zero-hit handling
    distinct from the generic ClinicalTrialsTool used by make_search_tool()."""
    return ClinicalTrialsSearchTool(
        {
            "name": "search_clinical_trials",
            "type": "ClinicalTrialsSearchTool",
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
def test_zero_hit_query_is_success_not_error(mock_get):
    """Fix-Round3-002: a well-formed query that legitimately matches zero
    trials must return status=success with an empty studies list, matching
    ClinicalTrials_search_by_intervention's behavior for the same case --
    not the hardcoded "no studies found" error string, which previously
    made a genuine zero-match result indistinguishable from an API/network
    failure and broke callers that parse JSON only on success."""
    mock_get.return_value = make_empty_studies_response()

    result = make_search_clinical_trials_tool().run(
        {"query_cond": "asdkjqwleqwe nonsense disease"}
    )

    assert result["status"] == "success"
    assert result["data"] == {"studies": [], "total_count": 0}


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


def make_adverse_events_tool():
    """Construct the actual `extract_clinical_trial_adverse_events` tool
    (type ClinicalTrialsDetailsTool)."""
    return ClinicalTrialsDetailsTool(
        {
            "name": "extract_clinical_trial_adverse_events",
            "type": "ClinicalTrialsDetailsTool",
            "tool_url": "/studies/{nctId}",
            "query_schema": {"adverse_event_type": "serious"},
            "parameter": {
                "type": "object",
                "properties": {
                    "nct_ids": {"type": "array"},
                    "organ_systems": {"type": "array"},
                    "adverse_event_type": {"type": "string"},
                },
            },
        }
    )


@pytest.mark.unit
@patch("requests.get")
def test_fetched_trial_with_no_matching_field_data_is_success_not_error(mock_get):
    """Fix-Round3-005: a real trial that was fetched successfully but simply
    has no adverse-event data posted yet (e.g. NOT_YET_RECRUITING) must
    return status=success with sparse data -- not the hardcoded "no
    relevant information found" error, which previously made this
    indistinguishable from every requested NCT ID being invalid/unreachable."""
    response = Mock()
    response.status_code = 200
    response.raise_for_status.return_value = None
    # A real, successfully-fetched study with no AdverseEventsModule posted.
    response.json.return_value = {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT07504601"},
        }
    }
    mock_get.return_value = response

    result = make_adverse_events_tool().run({"nct_ids": ["NCT07504601"]})

    assert result["status"] == "success"
    assert result["data"] == [{"NCT ID": "NCT07504601"}]


@pytest.mark.unit
@patch("requests.get")
def test_no_fetchable_trials_is_error(mock_get):
    """If every requested NCT ID fails to fetch at all (bad ID / API
    failure), that's still a genuine error, not a success with empty
    data. `execute_RESTful_query` signals this by returning False, which
    it does whenever the parsed response body contains an "error" key."""
    response = Mock()
    response.status_code = 404
    response.json.return_value = {"error": "study not found"}
    mock_get.return_value = response

    result = make_adverse_events_tool().run({"nct_ids": ["NCT00000000"]})

    assert result["status"] == "error"
