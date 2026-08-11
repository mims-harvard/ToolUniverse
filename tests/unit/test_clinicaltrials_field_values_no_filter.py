"""Regression guard for Fix-R36-1: ClinicalTrials_get_field_values advertised a
`query_cond` "condition filter" that the upstream endpoint has never had, so
every call that used the advertised parameter was a hard HTTP 400.

Live evidence (ClinicalTrials.gov API v2, probed directly with curl/requests):

    GET /api/v2/stats/fieldValues?fields=StdAge
        -> 200 [{"type":"ENUM","piece":"StdAge",...,"topValues":[
                  {"value":"ADULT","studiesCount":551190}, ...]}]
    GET /api/v2/stats/fieldValues?fields=StdAge&query.cond=asthma
        -> 400 "Invalid prefix in parameter name: query.cond"
    GET /api/v2/stats/fieldValues?fields=StdAge&filter.overallStatus=RECRUITING
        -> 400 "Invalid prefix in parameter name: filter.overallStatus"
    GET /api/v2/stats/fieldValues?fields=StdAge&filter.advanced=AREA[Condition]asthma
        -> 400 "Invalid prefix in parameter name: filter.advanced"
    GET /api/v2/stats/fieldValues?fields=StdAge&cond=asthma
        -> 400 "`cond` is unknown parameter"
    GET /api/v2/stats/fieldValues?fields=StdAge&query=asthma
        -> 400 "`query` is unknown parameter"
    GET /api/v2/stats/fieldValues?fields=StdAge&aggFilters=phase:3
        -> 400 "`aggFilters` is unknown parameter"

Only `fields` and `types` return 200 (the `/stats/field/values` path alias
behaves identically). The published OpenAPI description of the
`fieldValuesStats` operation likewise declares exactly two query parameters,
`types` ("Filter by field types") and `fields` ("Filter by piece names or field
paths of leaf fields") -- neither of which restricts the *population* the counts
are computed over.

So there is no filtered form to implement. The fix rejects `query_cond` at input
-- before any request is built -- and names the route that does work
(ClinicalTrials_search_studies + client-side tally), instead of letting the user
discover an opaque upstream 400. WHY reject rather than silently drop it: the
tool would otherwise return whole-registry counts while the caller believes they
are condition-scoped, which is a wrong answer dressed as a successful one.

These tests are fully mocked -- no network.
"""

import json

import pytest

from tooluniverse.ctg_tool import ClinicalTrialsTool

pytestmark = pytest.mark.unit

_CONFIG_PATH = "src/tooluniverse/data/clinicaltrials_gov_tools.json"
_TOOL_NAME = "ClinicalTrials_get_field_values"

# Shape of a real /stats/fieldValues 200 response, trimmed.
_LIVE_RESPONSE = [
    {
        "type": "ENUM",
        "piece": "StdAge",
        "field": "protocolSection.eligibilityModule.stdAges",
        "missingStudiesCount": 984,
        "uniqueValuesCount": 3,
        "topValues": [
            {"value": "ADULT", "studiesCount": 551190},
            {"value": "OLDER_ADULT", "studiesCount": 453760},
            {"value": "CHILD", "studiesCount": 115847},
        ],
    }
]


def _load_config():
    with open(_CONFIG_PATH) as f:
        tools = json.load(f)
    return next(t for t in tools if t["name"] == _TOOL_NAME)


def _make_tool():
    return ClinicalTrialsTool(_load_config())


# Fix-R37-1 added two auxiliary lookups to the successful path: /stats/size for
# the registry total (the denominator the facet lacks) and /stats/field/sizes
# for whether the field is list-valued (and so whether the rows double-count
# studies). Both are stubbed here so these R36-1 guards keep testing what they
# were written to test -- that `query_cond` never reaches the network and that
# the working call sends no query.* parameter -- rather than failing on the
# extra traffic.
_STATS_SIZE = {"totalStudies": 597913, "averageSizeBytes": 17275}
_LIST_FIELD_SIZES = [
    {"piece": "StdAge", "field": "protocolSection.eligibilityModule.stdAges"},
]


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _stub_get(seen=None):
    """Serve the three stats endpoints the tool now calls, recording only the
    /stats/fieldValues request -- the one these tests are about."""

    def _fake_get(url, params=None, timeout=None, **kwargs):
        if url.endswith("/stats/size"):
            return _FakeResponse(_STATS_SIZE)
        if url.endswith("/stats/field/sizes"):
            return _FakeResponse(_LIST_FIELD_SIZES)
        assert url.endswith("/stats/fieldValues"), url
        if seen is not None:
            seen["url"] = url
            seen["params"] = params
        return _FakeResponse(_LIVE_RESPONSE)

    return _fake_get


def test_query_cond_is_rejected_before_any_request(monkeypatch):
    """The broken call must never reach the network."""
    calls = []

    def _no_call(url, **kwargs):  # pragma: no cover - must not run
        calls.append(url)
        raise AssertionError(f"request should not have been issued: {url} {kwargs}")

    monkeypatch.setattr("requests.get", _no_call)

    result = _make_tool().run({"field": "StdAge", "query_cond": "apnea of prematurity"})

    assert calls == []
    assert result["status"] == "error"
    error = result["error"]
    # The message must explain the endpoint limitation, not just fail.
    assert "cannot filter field-value counts" in error
    # ... and must name the route that actually works.
    assert "ClinicalTrials_search_studies" in error
    # ... and echo back what the caller asked for, so the alternative is copy-pasteable.
    assert "apnea of prematurity" in error


def test_unfiltered_call_is_unchanged(monkeypatch):
    """Fix-R36-1 is input-validation only: the working call must be untouched,
    including the absence of any query.* parameter on the outgoing request."""
    seen = {}
    monkeypatch.setattr("requests.get", _stub_get(seen))

    result = _make_tool().run({"field": "StdAge"})

    assert seen["url"].endswith("/stats/fieldValues")
    assert seen["params"] == {"fields": "StdAge"}
    assert result["status"] == "success"
    assert result["data"]["field"] == "StdAge"
    assert result["data"]["values"] == [
        {"value": "ADULT", "studies_count": 551190},
        {"value": "OLDER_ADULT", "studies_count": 453760},
        {"value": "CHILD", "studies_count": 115847},
    ]
    # Fix-R37-1: this used to assert `"total_count": 3` as part of an exact
    # dict comparison, which encoded the very collision R37-1 removes --
    # `total_count` held the ROW count here and the matching-STUDY count in the
    # sibling ClinicalTrials_search_studies. The row count is now
    # `values_returned` and the facet's own cardinality is
    # `unique_values_count`; the exact-dict form is dropped because it made an
    # assertion about every future field of the response, which is not what
    # this R36-1 guard is for. See tests/unit/test_ctg_field_values_coverage.py
    # for the coverage fields themselves.
    assert "total_count" not in result["data"]
    assert result["data"]["values_returned"] == 3
    assert result["data"]["unique_values_count"] == 3
    assert result["data"]["missing_studies_count"] == 984


def test_null_query_cond_still_runs(monkeypatch):
    """query_cond is declared nullable; an explicit null must behave as absent
    rather than tripping the new rejection."""
    seen = {}
    monkeypatch.setattr("requests.get", _stub_get(seen))

    result = _make_tool().run({"field": "StdAge", "query_cond": None})
    assert result["status"] == "success"
    assert seen["params"] == {"fields": "StdAge"}


def test_config_no_longer_advertises_a_condition_filter():
    """The schema text is what agents read; leaving the old wording in place
    would keep steering them into the rejected call."""
    desc = _load_config()["parameter"]["properties"]["query_cond"]["description"]
    assert "NOT SUPPORTED" in desc
    assert "ClinicalTrials_search_studies" in desc
    assert "Optional condition filter" not in desc
