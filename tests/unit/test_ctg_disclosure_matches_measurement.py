"""Two ClinicalTrials.gov disclosures that described something other than the
measurement they sat next to.

Feature-53A-1 -- `relaxed_match_check.relaxed_query`

    `_relaxed_match_check` builds a probe from the caller's ORIGINAL wording
    for the rewritten parameters plus every other filter of the real query --
    deliberately, so the two counts are comparable, as the comment there says.
    It then published `relaxed`, the rewritten parameters ALONE, as
    `relaxed_query`, beside a count measured over the full probe. The published
    query was a strict subset of the counted one, and the gap ran in the
    direction that misleads. Measured live 2026-08-13:

        query_intr="levetiracetam", query_term="subcutaneous palliative"
          published  {"query.intr": "levetiracetam"}
          count      0
          note       "...a genuine absence of matching trials..."

        that published query, run on its own
          -> total_count 253

    A hospice pharmacist reads "no registered trials of levetiracetam" off a
    tool that is affirmatively claiming evidence of absence. The count was
    never wrong; only the disclosure was.

Feature-53A-3 -- `coverage_note` "The rows sum to ..."

    The sum is over the WHOLE facet, and with page_size=2 the reader is looking
    at two rows summing to something else. Live, {"field":"Phase",
    "page_size":2} returned NA=234,338 and PHASE2=89,726 (324,064) under the
    sentence "The rows sum to 481,189". A later sentence reconciles it, but
    this is the sentence a reader uses to check the arithmetic, and until they
    reach the later one it reads as arithmetic that does not work.
"""

import json
import socket
from pathlib import Path

import pytest
import requests

from tooluniverse.ctg_tool import ClinicalTrialsTool, _relaxed_match_check

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CONFIG_PATH = (
    _REPO_ROOT / "src" / "tooluniverse" / "data" / "clinicaltrials_gov_tools.json"
)


# --------------------------------------------------------------------------
# Feature-53A-1: the published query must be the counted query
# --------------------------------------------------------------------------

_REWRITES = [
    {
        "parameter": "query_intr",
        "api_field": "query.intr",
        "submitted": "levetiracetam",
        "executed": "(levetiracetam)",
    }
]
_PARAMS = {
    "query.intr": "(levetiracetam)",
    "query.term": "subcutaneous palliative",
    "filter.overallStatus": "RECRUITING",
    "pageSize": 5,
}


def _check(total, params=None):
    seen = {}

    def fetch_total_count(probe):
        seen["probe"] = probe
        return total

    result = _relaxed_match_check(dict(params or _PARAMS), _REWRITES, fetch_total_count)
    return result, seen["probe"]


def test_the_published_query_is_the_one_that_was_counted():
    """Pre-fix: `{"query.intr": "levetiracetam"}` -- query.term absent."""
    check, probe = _check(total=0)

    assert check["relaxed_query"] == {
        "query.intr": "levetiracetam",
        "query.term": "subcutaneous palliative",
        "filter.overallStatus": "RECRUITING",
    }
    for field, value in check["relaxed_query"].items():
        assert probe[field] == value


def test_every_inherited_filter_appears_not_only_the_rewritten_one():
    """The gap was every OTHER filter, so one extra key is not enough."""
    check, _ = _check(total=0)

    assert set(check["relaxed_query"]) == {
        "query.intr",
        "query.term",
        "filter.overallStatus",
    }


def test_paging_parameters_are_not_mistaken_for_filters():
    """`pageSize`, `fields` and `countTotal` do not decide which studies match."""
    check, _ = _check(total=0)

    assert not {"pageSize", "fields", "countTotal", "pageToken"} & set(
        check["relaxed_query"]
    )


def test_the_evidence_of_absence_claim_now_matches_what_was_measured():
    """The note is an affirmative claim; it must describe the shown query."""
    check, _ = _check(total=0)

    assert "genuine absence of matching trials" in check["note"]
    assert check["relaxed_query"]["query.term"] == "subcutaneous palliative"


def test_a_real_false_negative_is_still_reported_as_one():
    """The other branch must be untouched by the disclosure change."""
    check, _ = _check(total=253)

    assert "LIKELY FALSE NEGATIVE" in check["note"]
    assert "253" in check["note"]


def test_a_failed_probe_still_degrades_instead_of_erroring():
    def raising(_probe):
        raise requests.exceptions.ConnectionError("boom")

    check = _relaxed_match_check(dict(_PARAMS), _REWRITES, raising)

    assert check["relaxed_total_count"] is None
    assert "treat this 0 as unverified" in check["note"]


# --------------------------------------------------------------------------
# Feature-53A-3: the sum sentence must say which rows it means
# --------------------------------------------------------------------------

_PHASE_VALUES = [
    {
        "type": "ENUM",
        "piece": "Phase",
        "field": "protocolSection.designModule.phases",
        "missingStudiesCount": 141862,
        "uniqueValuesCount": 6,
        "topValues": [
            {"value": "NA", "studiesCount": 234338},
            {"value": "PHASE2", "studiesCount": 89726},
            {"value": "PHASE1", "studiesCount": 65384},
            {"value": "PHASE3", "studiesCount": 49625},
            {"value": "PHASE4", "studiesCount": 35631},
            {"value": "EARLY_PHASE1", "studiesCount": 6485},
        ],
    }
]
_FACET_SUM = 481189
_SHOWN_SUM = 324064  # NA + PHASE2, the two rows page_size=2 returns

_LIST_FIELD_SIZES = [{"piece": "Phase", "field": "protocolSection.designModule.phases"}]
_STATS_SIZE = {"totalStudies": 598509, "averageSizeBytes": 17275}


class _FakeResponse:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def _blocked(*args, **kwargs):
        raise AssertionError(f"network access attempted: {args!r} {kwargs!r}")

    monkeypatch.setattr(requests, "request", _blocked)
    monkeypatch.setattr(requests.Session, "request", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)
    monkeypatch.setattr(requests, "get", _blocked)


@pytest.fixture
def tool(monkeypatch):
    def _fake_get(url, params=None, timeout=None, **kwargs):
        if url.endswith("/stats/fieldValues"):
            return _FakeResponse(_PHASE_VALUES)
        if url.endswith("/stats/field/sizes"):
            return _FakeResponse(_LIST_FIELD_SIZES)
        if url.endswith("/stats/size"):
            return _FakeResponse(_STATS_SIZE)
        raise AssertionError(f"unexpected URL: {url}")

    monkeypatch.setattr(requests, "get", _fake_get)
    with open(_CONFIG_PATH) as f:
        config = next(
            t for t in json.load(f) if t["name"] == "ClinicalTrials_get_field_values"
        )
    return ClinicalTrialsTool(config)


def test_a_truncated_page_says_the_sum_is_over_the_whole_facet(tool):
    """Pre-fix: "The rows sum to 481,189" above two rows summing to 324,064."""
    note = tool.run({"field": "Phase", "page_size": 2})["data"]["coverage_note"]

    assert "The rows sum to" not in note
    assert f"All 6 rows of the facet sum to {_FACET_SUM:,}" in note
    assert "the 2 shown below are only part of that" in note


def test_the_shown_rows_do_not_sum_to_the_published_figure(tool):
    """The premise, asserted rather than assumed."""
    data = tool.run({"field": "Phase", "page_size": 2})["data"]

    assert sum(row["studies_count"] for row in data["values"]) == _SHOWN_SUM
    assert _SHOWN_SUM != _FACET_SUM


def test_an_untruncated_page_keeps_the_plain_wording(tool):
    """Nothing to disambiguate when the rows shown ARE the facet."""
    note = tool.run({"field": "Phase", "page_size": 20})["data"]["coverage_note"]

    assert f"The rows sum to {_FACET_SUM:,}" in note
    assert "rows of the facet sum to" not in note
