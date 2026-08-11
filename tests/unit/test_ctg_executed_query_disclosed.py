"""The ClinicalTrials search tools must disclose the query they really ran.

Feature-R33-1. ``_phrase_quote_if_plain`` and ``_restrict_to_area`` rewrite the
caller's wording before it is sent: a plain multi-word value becomes an exact
Essie phrase, and an intervention/sponsor is further narrowed to specific
AREA[] fields. Both rewrites are deliberate and load-bearing -- they are what
Fix-R9D-1, Fix-R13B-1 and Fix-R23-1 installed to stop 'cervical cancer' ranking
oesophageal trials and 'vedolizumab' surfacing unrelated oncology studies -- so
removing them would only trade a false negative for the false positives they
were fixing. The hazard they create is that the query that runs is not the
query that was asked for, and a rewrite matching nothing came back as an
ordinary, successful "0 studies" with nothing to say a rewrite had happened.

Verified live before the fix::

    ClinicalTrials_search_by_intervention
        {"intervention": "donor derived cell therapy", "page_size": 5}
      -> {"status": "success", "data": {"studies": [], "total_count": 0}}

    query.intr=donor derived cell therapy                     -> totalCount 251
    query.intr=(AREA[InterventionName]"donor derived cell therapy" OR
               AREA[InterventionOtherName]"donor derived cell therapy")
                                                              -> totalCount 0
    query.cond=kidney transplantation                         -> totalCount 2863
    query.cond="kidney transplantation"                       -> totalCount 2436

The fix is additive: the returned studies are untouched, and a zero that
followed a rewrite now carries ``relaxed_match_check`` naming the count the
caller's own wording would have matched. A parenthesised value is the escape
hatch -- both helpers bail out on Essie syntax, so '(donor derived cell
therapy)' reaches the API verbatim and matches the same 251 studies.

All assertions run against synthetic ClinicalTrials.gov payloads -- no network.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

import tooluniverse
from tooluniverse.ctg_tool import ClinicalTrialsSearchTool, ClinicalTrialsTool

pytestmark = pytest.mark.unit

CONFIG = Path(tooluniverse.__file__).parent / "data/clinicaltrials_gov_tools.json"
CONFIGS = json.loads(CONFIG.read_text())

INTR_EXECUTED = (
    '(AREA[InterventionName]"donor derived cell therapy" OR '
    'AREA[InterventionOtherName]"donor derived cell therapy")'
)
RELAXED_TOTAL = 251


def _config(name):
    return next(c for c in CONFIGS if c["name"] == name)


def _study(nct_id="NCT01234567"):
    return {
        "protocolSection": {
            "identificationModule": {"nctId": nct_id, "briefTitle": "A real trial"},
            "designModule": {"phases": ["PHASE3"]},
        }
    }


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _run(arguments, studies=(), relaxed_total=RELAXED_TOTAL, probe_fails=False):
    """Drive ClinicalTrials_search_by_intervention against a mocked requests.get.

    The first call is the search; any second call is the relaxed-wording probe.
    Returns (list_of_request_params, result).
    """
    calls = []
    studies = list(studies)

    def fake_get(url, params=None, timeout=None):
        calls.append(dict(params))
        if len(calls) == 1:
            return _Resp({"studies": studies, "totalCount": len(studies)})
        if probe_fails:
            raise ConnectionError("clinicaltrials.gov unreachable")
        return _Resp({"studies": [], "totalCount": relaxed_total})

    tool = ClinicalTrialsTool(_config("ClinicalTrials_search_by_intervention"))
    with patch("requests.get", side_effect=fake_get):
        result = tool.run(dict(arguments))
    return calls, result


def _run_search_tool(arguments, studies=(), relaxed_total=RELAXED_TOTAL):
    """Same, for search_clinical_trials, which goes through execute_RESTful_query."""
    calls = []
    studies = list(studies)

    def fake_query(endpoint_url, variables):
        calls.append(dict(variables))
        if len(calls) == 1:
            return {"studies": studies, "totalCount": len(studies)}
        return {"studies": [], "totalCount": relaxed_total}

    tool = ClinicalTrialsSearchTool(_config("search_clinical_trials"))
    with patch("tooluniverse.ctg_tool.execute_RESTful_query", side_effect=fake_query):
        result = tool.run(dict(arguments))
    return calls, result


# --- 1. the executed query is disclosed -------------------------------------


def test_executed_query_is_reported_and_differs_from_what_was_asked():
    calls, result = _run({"intervention": "donor derived cell therapy"})
    data = result["data"]

    # What ran is exactly what was sent upstream.
    assert data["executed_query"]["query.intr"] == INTR_EXECUTED
    assert calls[0]["query.intr"] == INTR_EXECUTED
    # ...and it is not what the caller typed, which is the whole point.
    assert data["executed_query"]["query.intr"] != "donor derived cell therapy"


def test_query_rewrites_name_the_parameter_and_the_restricted_fields():
    _, result = _run({"intervention": "donor derived cell therapy"})

    (rewrite,) = result["data"]["query_rewrites"]
    assert rewrite["parameter"] == "intervention"
    assert rewrite["api_field"] == "query.intr"
    assert rewrite["submitted"] == "donor derived cell therapy"
    assert rewrite["executed"] == INTR_EXECUTED
    assert rewrite["restricted_to_fields"] == [
        "InterventionName",
        "InterventionOtherName",
    ]


def test_condition_phrase_quoting_is_disclosed_too():
    _, result = _run(
        {"intervention": "nivolumab", "condition": "kidney transplantation"},
        studies=[_study()],
    )

    data = result["data"]
    assert data["executed_query"]["query.cond"] == '"kidney transplantation"'
    cond = next(r for r in data["query_rewrites"] if r["api_field"] == "query.cond")
    assert cond["submitted"] == "kidney transplantation"
    assert cond["executed"] == '"kidney transplantation"'
    # Quoting narrows without restricting to a named field.
    assert cond["restricted_to_fields"] == []


def test_disclosure_is_present_on_a_successful_non_empty_search():
    """ "What ran" must be visible on every response, not only on failures."""
    _, result = _run({"intervention": "nivolumab"}, studies=[_study()])

    assert result["status"] == "success"
    assert result["data"]["executed_query"]["query.intr"]
    assert result["data"]["query_rewrites"]


# --- 2. a zero result is self-diagnosing ------------------------------------


def test_zero_hit_rewrite_reports_the_relaxed_match_count():
    _, result = _run({"intervention": "donor derived cell therapy"}, studies=[])
    check = result["data"]["relaxed_match_check"]

    assert check["relaxed_total_count"] == RELAXED_TOTAL
    assert check["relaxed_query"] == {"query.intr": "donor derived cell therapy"}
    assert "LIKELY FALSE NEGATIVE" in check["note"]
    assert str(RELAXED_TOTAL) in check["note"]


def test_zero_hit_note_names_the_escape_hatch():
    _, result = _run({"intervention": "donor derived cell therapy"}, studies=[])
    note = result["data"]["relaxed_match_check"]["note"]

    # The parenthesised form is passed through unrewritten (see below), and
    # query_term is the free-text alternative.
    assert 'intervention="(donor derived cell therapy)"' in note
    assert "query_term" in note


def test_the_returned_studies_stay_empty_and_the_call_stays_successful():
    """The relaxed results must never be silently substituted."""
    _, result = _run({"intervention": "donor derived cell therapy"}, studies=[])

    assert result["status"] == "success"
    assert result["data"]["studies"] == []
    assert result["data"]["total_count"] == 0


def test_the_probe_is_comparable_to_the_primary_query():
    """A probe with different filters would report an incomparable count."""
    calls, _ = _run(
        {"intervention": "donor derived cell therapy", "filter_phase": "PHASE3"},
        studies=[],
    )
    primary, probe = calls

    assert probe["query.intr"] == "donor derived cell therapy"
    assert probe["filter.advanced"] == primary["filter.advanced"]
    # Cheapest request that still yields a count.
    assert probe["pageSize"] == 1
    assert probe["countTotal"] == "true"


def test_a_genuine_zero_is_reported_as_a_genuine_zero():
    _, result = _run(
        {"intervention": "asdkjqwleqwe nonsense drug"}, studies=[], relaxed_total=0
    )
    check = result["data"]["relaxed_match_check"]

    assert check["relaxed_total_count"] == 0
    assert "genuine absence" in check["note"]
    assert "FALSE NEGATIVE" not in check["note"]


# --- 3. the probe costs nothing on the common path --------------------------


def test_no_probe_when_the_search_returned_results():
    calls, result = _run({"intervention": "nivolumab"}, studies=[_study()])

    assert len(calls) == 1
    assert "relaxed_match_check" not in result["data"]


def test_no_probe_when_nothing_was_rewritten():
    """A single-word sponsor/intervention still gets AREA-restricted, but a
    value the caller wrote in Essie syntax is passed through untouched -- there
    is then no rewrite to blame for the zero."""
    calls, result = _run({"intervention": "AREA[BriefSummary]Luxturna"}, studies=[])

    assert len(calls) == 1
    assert result["data"]["query_rewrites"] == []
    assert "relaxed_match_check" not in result["data"]


def test_parenthesised_value_is_the_documented_escape_hatch():
    calls, result = _run({"intervention": "(donor derived cell therapy)"}, studies=[])

    assert calls[0]["query.intr"] == "(donor derived cell therapy)"
    assert result["data"]["query_rewrites"] == []


# --- 4. a failed probe degrades, it does not error --------------------------


def test_a_failed_probe_keeps_todays_output_and_says_the_check_was_unavailable():
    _, result = _run(
        {"intervention": "donor derived cell therapy"}, studies=[], probe_fails=True
    )
    check = result["data"]["relaxed_match_check"]

    assert result["status"] == "success"
    assert result["data"]["studies"] == []
    assert result["data"]["executed_query"]["query.intr"] == INTR_EXECUTED
    assert check["relaxed_total_count"] is None
    assert "could not be checked" in check["note"]
    assert "ConnectionError" in check["note"]


# --- 5. the other code path behaves identically -----------------------------


def test_search_clinical_trials_discloses_and_diagnoses_the_same_way():
    calls, result = _run_search_tool(
        {"intervention": "donor derived cell therapy"}, studies=[]
    )
    data = result["data"]

    assert data["executed_query"]["query.intr"] == INTR_EXECUTED
    assert data["query_rewrites"][0]["parameter"] == "intervention"
    assert data["studies"] == []
    assert data["relaxed_match_check"]["relaxed_total_count"] == RELAXED_TOTAL
    assert calls[1]["query.intr"] == "donor derived cell therapy"


def test_search_clinical_trials_also_discloses_its_phase_gate():
    """The hardcoded phase>=2 filter is part of what really ran."""
    _, result = _run_search_tool({"intervention": "nivolumab"}, studies=[_study()])

    assert result["data"]["executed_query"]["filter.advanced"] == (
        "(AREA[Phase]PHASE2 OR AREA[Phase]PHASE3 OR AREA[Phase]PHASE4)"
    )


def test_search_clinical_trials_keeps_its_existing_zero_result_note():
    """The Feature-27A-2 explanation must survive alongside the new keys."""
    _, result = _run_search_tool({"intervention": "Luxturna"}, studies=[])

    assert "InterventionOtherName" in result["metadata"]["note"]


# --- 6. the config documents all of it --------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        "search_clinical_trials",
        "ClinicalTrials_search_studies",
        "ClinicalTrials_search_by_intervention",
        "ClinicalTrials_search_by_sponsor",
    ],
)
def test_every_rewriting_tool_documents_the_rewrite_and_the_new_keys(name):
    cfg = _config(name)

    assert "executed_query" in cfg["description"]
    assert "relaxed_match_check" in cfg["description"]
    assert "EXACT PHRASE" in cfg["description"]

    branch = next(
        b
        for b in cfg["return_schema"]["oneOf"]
        if isinstance(b.get("properties"), dict) and "studies" in b["properties"]
    )
    props = branch["properties"]
    assert props["executed_query"]["type"] == "object"
    assert props["query_rewrites"]["type"] == "array"
    assert props["relaxed_match_check"]["properties"]["relaxed_total_count"][
        "type"
    ] == ["integer", "null"]


@pytest.mark.parametrize(
    "name,param",
    [
        ("search_clinical_trials", "intervention"),
        ("ClinicalTrials_search_studies", "intervention"),
        ("ClinicalTrials_search_studies", "query_cond"),
        ("ClinicalTrials_search_studies", "condition"),
        ("ClinicalTrials_search_by_intervention", "intervention"),
        ("ClinicalTrials_search_by_intervention", "condition"),
        ("ClinicalTrials_search_by_sponsor", "sponsor"),
        ("ClinicalTrials_search_by_sponsor", "query_cond"),
    ],
)
def test_rewritten_parameters_document_the_phrase_match_and_escape_hatch(name, param):
    description = _config(name)["parameter"]["properties"][param]["description"]

    assert "EXACT PHRASE" in description or "exact phrase" in description
    assert "parentheses" in description
