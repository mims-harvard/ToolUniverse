"""Regression guards for Fix-R37-1: ClinicalTrials_get_field_values reported a
facet without its denominator, ignored a documented parameter, and named its
row count `total_count` -- the same key the sibling search tool uses for a
matching-study count.

Three defects, all CLI-verified against the live API before the fix:

1. The denominator was thrown away. `/stats/field/values?fields=Phase` returns
   `missingStudiesCount: 141728` and `uniqueValuesCount: 6` alongside the rows;
   the tool kept only the rows. An analyst reading "PHASE3 49,625" divided by
   the 480,714 the rows sum to and got 10.3%, never learning that 141,728
   studies had been excluded from the facet outright.

   The rows do NOT reconcile to the registry in either direction, and the two
   errors run OPPOSITE ways -- which is why naming only one of them is worse
   than useless:

       rows sum                                          480,714
       + studies recording no phase (excluded)         + 141,728
       =                                                 622,442
       registry total (/stats/size totalStudies)         597,913
       difference                                       + 24,529

   The 24,529 is not slop: `protocolSection.designModule.phases` is a LIST, and
   `/stats/field/sizes?fields=Phase` reports exactly 24,529 studies with size 2
   (431,656 with size 1). Those studies are counted in two rows each. So
   431,656 + 24,529 = 456,185 studies record a phase, 456,185 + 141,728 =
   597,913 = the registry total, exactly. The facet is simultaneously short by
   the excluded studies and long by the double-counted ones.

2. `page_size` was declared, documented ("Number of field values to return
   (default 50)") and never read. Verified live: {"field":"Phase",
   "page_size":2} returned all 6 rows; {"field":"OverallStatus","page_size":3}
   returned all 14.

3. `total_count` here meant "rows returned" (6). In ClinicalTrials_search_studies
   -- same category, same tool family -- `total_count` means "studies matching".
   One name, two incompatible meanings, and the wrong reading is the plausible
   one.

How array-ness is decided (see `_list_valued_field_paths`): NOT by the plural in
the field path. `/stats/field/sizes` with no `fields` parameter returns exactly
the field paths that are lists; a scalar field 404s. A leaf is multi-valued if
its own path is in that set OR any ancestor path is -- InterventionType is a
scalar `type` inside the `interventions` LIST, so it 404s on its own name yet
its rows sum to 616,289 against 597,913 registered studies.

These tests are fully hermetic: `requests.get`, `requests.request`,
`requests.Session.request` and `socket.create_connection` are all patched, the
last three to raise, so any code path other than the stubbed `requests.get`
fails loudly instead of reaching the network.
"""

import json
import socket
from pathlib import Path

import pytest
import requests

from tooluniverse.ctg_tool import ClinicalTrialsTool

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CONFIG_PATH = (
    _REPO_ROOT / "src" / "tooluniverse" / "data" / "clinicaltrials_gov_tools.json"
)
_TOOL_NAME = "ClinicalTrials_get_field_values"

_REGISTRY_TOTAL = 597913

# Verbatim shape of the live /stats/field/values?fields=Phase 200 response.
_PHASE_VALUES = [
    {
        "type": "ENUM",
        "piece": "Phase",
        "field": "protocolSection.designModule.phases",
        "missingStudiesCount": 141728,
        "uniqueValuesCount": 6,
        "topValues": [
            {"value": "NA", "studiesCount": 234000},
            {"value": "PHASE2", "studiesCount": 89682},
            {"value": "PHASE1", "studiesCount": 65343},
            {"value": "PHASE3", "studiesCount": 49625},
            {"value": "PHASE4", "studiesCount": 35631},
            {"value": "EARLY_PHASE1", "studiesCount": 6433},
        ],
    }
]
_PHASE_ROWS_SUM = 480714
_PHASE_STUDIES_WITH_VALUE = 456185
_PHASE_DUPLICATES = 24529

# A scalar field: one value per study, so the rows partition the subset.
_STUDY_TYPE_VALUES = [
    {
        "type": "ENUM",
        "piece": "StudyType",
        "field": "protocolSection.designModule.studyType",
        "missingStudiesCount": 984,
        "uniqueValuesCount": 3,
        "topValues": [
            {"value": "INTERVENTIONAL", "studiesCount": 453832},
            {"value": "OBSERVATIONAL", "studiesCount": 141262},
            {"value": "EXPANDED_ACCESS", "studiesCount": 1835},
        ],
    }
]

# A scalar leaf inside a list of structs: 404s on /stats/field/sizes under its
# own name, but double-counts because `interventions` is the list. Rows trimmed
# to 6 with uniqueValuesCount matched, so the arithmetic stays exact.
_INTERVENTION_TYPE_VALUES = [
    {
        "type": "ENUM",
        "piece": "InterventionType",
        "field": "protocolSection.armsInterventionsModule.interventions.type",
        "missingStudiesCount": 60529,
        "uniqueValuesCount": 6,
        "topValues": [
            {"value": "DRUG", "studiesCount": 300000},
            {"value": "OTHER", "studiesCount": 120000},
            {"value": "BEHAVIORAL", "studiesCount": 80000},
            {"value": "PROCEDURE", "studiesCount": 50000},
            {"value": "DEVICE", "studiesCount": 40000},
            {"value": "DIETARY_SUPPLEMENT", "studiesCount": 26289},
        ],
    }
]
_INTERVENTION_TYPE_DUPLICATES = 78905  # 616,289 + 60,529 - 597,913

# High cardinality: ClinicalTrials.gov caps topValues at 250 of 132,704, so the
# rows are a partial sum and no excess can be derived from them.
_CONDITION_VALUES = [
    {
        "type": "STRING",
        "piece": "Condition",
        "field": "protocolSection.conditionsModule.conditions",
        "missingStudiesCount": 1021,
        "uniqueValuesCount": 132704,
        "topValues": [
            {"value": "Healthy", "studiesCount": 12000},
            {"value": "Breast Cancer", "studiesCount": 9000},
            {"value": "Obesity", "studiesCount": 7000},
        ],
    }
]

# /stats/field/sizes with no `fields` parameter: the list-valued field paths.
# Trimmed from the 71 the live API returns; note studyType and overallStatus are
# absent, and `interventions` is present while `interventions.type` is not.
_LIST_FIELD_SIZES = [
    {"piece": "Phase", "field": "protocolSection.designModule.phases"},
    {"piece": "Condition", "field": "protocolSection.conditionsModule.conditions"},
    {
        "piece": "Intervention",
        "field": "protocolSection.armsInterventionsModule.interventions",
    },
    {"piece": "StdAge", "field": "protocolSection.eligibilityModule.stdAges"},
]

_STATS_SIZE = {"totalStudies": _REGISTRY_TOTAL, "averageSizeBytes": 17275}

_VALUES_BY_FIELD = {
    "Phase": _PHASE_VALUES,
    "StudyType": _STUDY_TYPE_VALUES,
    "InterventionType": _INTERVENTION_TYPE_VALUES,
    "Condition": _CONDITION_VALUES,
}


def _load_config():
    with open(_CONFIG_PATH) as f:
        tools = json.load(f)
    return next(t for t in tools if t["name"] == _TOOL_NAME)


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Every escape route to the network raises.

    `requests.get` is left for the individual tests to stub; everything else --
    including the machinery `requests.get` itself would use if it were NOT
    stubbed -- is wired to raise, so a missed patch surfaces as a loud error
    rather than a silent live call.
    """

    def _blocked(*args, **kwargs):
        raise AssertionError(f"network access attempted: {args!r} {kwargs!r}")

    monkeypatch.setattr(requests, "request", _blocked)
    monkeypatch.setattr(requests.Session, "request", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)
    monkeypatch.setattr(requests, "get", _blocked)


@pytest.fixture
def calls():
    return []


@pytest.fixture
def tool(monkeypatch, calls):
    """A tool whose three GETs are served from the fixtures above."""

    def _fake_get(url, params=None, timeout=None, **kwargs):
        calls.append((url, params))
        if url.endswith("/stats/fieldValues"):
            field = (params or {}).get("fields")
            if field not in _VALUES_BY_FIELD:
                return _FakeResponse(None, status_code=404)
            return _FakeResponse(_VALUES_BY_FIELD[field])
        if url.endswith("/stats/field/sizes"):
            return _FakeResponse(_LIST_FIELD_SIZES)
        if url.endswith("/stats/size"):
            return _FakeResponse(_STATS_SIZE)
        raise AssertionError(f"unexpected URL: {url}")

    monkeypatch.setattr(requests, "get", _fake_get)
    return ClinicalTrialsTool(_load_config())


# --------------------------------------------------------------------------
# Defect 1 -- the facet's own denominator
# --------------------------------------------------------------------------


def test_missing_and_unique_counts_are_surfaced(tool):
    """The two numbers upstream sends with the rows must reach the caller."""
    data = tool.run({"field": "Phase"})["data"]

    assert data["missing_studies_count"] == 141728
    assert data["unique_values_count"] == 6


def test_registry_total_and_usable_denominators_are_provided(tool):
    """Surfacing the exclusion is only useful with something to divide by."""
    data = tool.run({"field": "Phase"})["data"]

    assert data["total_studies_in_registry"] == _REGISTRY_TOTAL
    # The subset the facet actually represents.
    assert data["studies_with_value"] == _PHASE_STUDIES_WITH_VALUE
    assert data["studies_with_value"] == _REGISTRY_TOTAL - 141728


def test_double_counted_studies_are_quantified(tool):
    """rows + excluded overshoots the registry by exactly the multi-phase studies."""
    data = tool.run({"field": "Phase"})["data"]

    assert data["is_multi_valued"] is True
    assert data["duplicate_studies_count"] == _PHASE_DUPLICATES
    # The reconciliation the note asserts, checked arithmetically.
    rows_sum = sum(v["studies_count"] for v in data["values"])
    assert rows_sum == _PHASE_ROWS_SUM
    assert (
        rows_sum + data["missing_studies_count"] - _REGISTRY_TOTAL == _PHASE_DUPLICATES
    )
    assert data["studies_with_value"] + data["missing_studies_count"] == _REGISTRY_TOTAL


def test_coverage_note_names_both_distortions(tool):
    """Naming one distortion and not the other is worse than naming neither:
    the reader confidently corrects in one direction and stays wrong."""
    note = tool.run({"field": "Phase"})["data"]["coverage_note"]

    # (a) studies excluded from the facet entirely
    assert "141,728" in note
    assert "EXCLUDED" in note
    assert "bucketed as unknown" in note
    # (b) studies counted in more than one row
    assert "multi-valued" in note
    assert "24,529" in note
    assert "SEVERAL rows" in note
    # ... and that the two disagree in direction, which is the whole point.
    assert "OPPOSITE directions" in note
    # ... plus what may and may not be divided by.
    assert "480,714" in note
    assert "do NOT use it as a denominator" in note
    assert "total_studies_in_registry" in note
    assert "studies_with_value" in note


def test_single_valued_field_is_not_accused_of_double_counting(tool):
    """The disclosure has to be per-field, not a blanket warning bolted onto
    every response -- a warning that is always printed is never read."""
    data = tool.run({"field": "StudyType"})["data"]

    assert data["is_multi_valued"] is False
    assert data["duplicate_studies_count"] == 0
    note = data["coverage_note"]
    assert "at most one value per study" in note
    assert "do not double-count" in note
    assert "OPPOSITE directions" not in note
    # The exclusion is still disclosed, small as it is.
    assert "984" in note
    assert "EXCLUDED" in note


def test_array_ness_is_detected_through_an_ancestor_list(tool):
    """InterventionType is a scalar `type` inside the `interventions` LIST, so
    it 404s on /stats/field/sizes under its own name. Trusting that 404 would
    declare it single-valued while its rows overshoot the registry by 78,905."""
    data = tool.run({"field": "InterventionType"})["data"]

    assert (
        data["field_path"]
        == "protocolSection.armsInterventionsModule.interventions.type"
    )
    assert data["is_multi_valued"] is True
    assert data["duplicate_studies_count"] == _INTERVENTION_TYPE_DUPLICATES
    assert "multi-valued" in data["coverage_note"]


def test_upstream_capped_ranking_refuses_to_derive_an_excess(tool):
    """With only the top 250 of 132,704 values the rows are a partial sum, so
    the subtraction is meaningless -- report null rather than a wrong number."""
    data = tool.run({"field": "Condition"})["data"]

    assert data["unique_values_count"] == 132704
    assert data["truncated"] is True
    assert data["duplicate_studies_count"] is None
    note = data["coverage_note"]
    assert "132,704" in note
    assert "partial sum" in note
    assert "not a denominator for anything" in note


def test_failed_auxiliary_lookups_degrade_instead_of_fabricating(monkeypatch, calls):
    """If the registry total and list-field lookups fail, say so -- never print
    a denominator that was guessed."""

    def _fake_get(url, params=None, timeout=None, **kwargs):
        calls.append((url, params))
        if url.endswith("/stats/fieldValues"):
            return _FakeResponse(_PHASE_VALUES)
        return _FakeResponse(None, status_code=503)

    monkeypatch.setattr(requests, "get", _fake_get)
    data = ClinicalTrialsTool(_load_config()).run({"field": "Phase"})["data"]

    assert data["total_studies_in_registry"] is None
    assert data["studies_with_value"] is None
    assert data["is_multi_valued"] is None
    assert data["duplicate_studies_count"] is None
    # The rows and the exclusion are still reported -- they came from the call
    # that succeeded.
    assert data["missing_studies_count"] == 141728
    note = data["coverage_note"]
    assert "could not be determined" in note
    assert "141,728" in note


# --------------------------------------------------------------------------
# Defect 2 -- page_size was documented and ignored
# --------------------------------------------------------------------------


def test_page_size_truncates_and_flags_the_truncation(tool):
    """Verified live before the fix: page_size=2 returned all 6 rows."""
    data = tool.run({"field": "Phase", "page_size": 2})["data"]

    assert len(data["values"]) == 2
    assert [v["value"] for v in data["values"]] == ["NA", "PHASE2"]
    assert data["values_returned"] == 2
    assert data["truncated"] is True
    # The true size of the facet survives the truncation, so a cut list can
    # never be mistaken for the whole one.
    assert data["unique_values_count"] == 6
    note = data["coverage_note"]
    assert "page_size=2" in note
    assert "top 2 of 6" in note


def test_untruncated_page_size_is_not_flagged(tool):
    """page_size larger than the facet must not raise a false truncation flag."""
    data = tool.run({"field": "Phase", "page_size": 20})["data"]

    assert data["values_returned"] == 6
    assert data["truncated"] is False
    assert "page_size=" not in data["coverage_note"]


def test_page_size_defaults_to_fifty(tool):
    data = tool.run({"field": "Phase"})["data"]
    assert data["values_returned"] == 6
    assert data["truncated"] is False


def test_facet_wide_figures_ignore_page_size(tool):
    """Truncating the display must not silently shrink the denominators."""
    full = tool.run({"field": "Phase"})["data"]
    cut = tool.run({"field": "Phase", "page_size": 1})["data"]

    for key in (
        "unique_values_count",
        "missing_studies_count",
        "total_studies_in_registry",
        "studies_with_value",
        "duplicate_studies_count",
    ):
        assert cut[key] == full[key], key


@pytest.mark.parametrize("bad", [0, -3])
def test_non_positive_page_size_is_rejected(tool, bad):
    result = tool.run({"field": "Phase", "page_size": bad})
    assert result["status"] == "error"
    assert "page_size must be a positive integer" in result["error"]


def test_unparseable_page_size_is_rejected(tool):
    result = tool.run({"field": "Phase", "page_size": "lots"})
    assert result["status"] == "error"
    assert "page_size must be a positive integer" in result["error"]


# --------------------------------------------------------------------------
# Defect 3 -- the total_count naming collision
# --------------------------------------------------------------------------


def test_total_count_is_gone(tool):
    """`total_count` meant 'rows returned' here and 'matching studies' in
    ClinicalTrials_search_studies. No alias was kept: an alias under the
    colliding NAME preserves exactly the ambiguity being fixed, and the two
    quantities it conflated are both present under unambiguous names."""
    data = tool.run({"field": "Phase"})["data"]

    assert "total_count" not in data
    # Both meanings are available, each named for what it is.
    assert data["values_returned"] == 6  # the old value of total_count
    assert data["unique_values_count"] == 6  # distinct values in the facet


def test_the_two_counts_separate_when_they_differ(tool):
    """With page_size applied the old single number could not have expressed
    both, which is what made the collision load-bearing rather than cosmetic."""
    data = tool.run({"field": "Phase", "page_size": 2})["data"]

    assert data["values_returned"] == 2
    assert data["unique_values_count"] == 6


def test_config_declares_the_new_keys_and_not_total_count():
    """The return_schema is what downstream agents read; leaving total_count in
    it would keep advertising the collision."""
    schema = _load_config()["return_schema"]["oneOf"][0]["properties"]

    assert "total_count" not in schema
    for key in (
        "unique_values_count",
        "values_returned",
        "truncated",
        "missing_studies_count",
        "total_studies_in_registry",
        "studies_with_value",
        "is_multi_valued",
        "duplicate_studies_count",
        "coverage_note",
    ):
        assert key in schema, key


# --------------------------------------------------------------------------
# Cost of the two auxiliary lookups
# --------------------------------------------------------------------------


def test_auxiliary_lookups_are_fetched_once_per_instance(tool, calls):
    """The denominator and the list-field set are the same for every field, so
    paying for them on each call would triple this tool's request count for
    nothing."""
    tool.run({"field": "Phase"})
    tool.run({"field": "StudyType"})
    tool.run({"field": "Condition"})

    endpoints = [url.rsplit("/api/v2", 1)[-1] for url, _ in calls]
    assert endpoints.count("/stats/fieldValues") == 3
    assert endpoints.count("/stats/size") == 1
    assert endpoints.count("/stats/field/sizes") == 1


def test_a_failed_auxiliary_lookup_is_not_retried_on_every_call(monkeypatch, calls):
    """Failures are memoised for a short window too. Without that, an outage of
    either stats endpoint charges EVERY call two fresh timeouts stacked on the
    primary request -- the rows are already in hand, so a lost denominator must
    not become a latency problem."""

    def _fake_get(url, params=None, timeout=None, **kwargs):
        calls.append((url, params))
        if url.endswith("/stats/fieldValues"):
            return _FakeResponse(_PHASE_VALUES)
        return _FakeResponse(None, status_code=503)

    monkeypatch.setattr(requests, "get", _fake_get)
    tool = ClinicalTrialsTool(_load_config())

    tool.run({"field": "Phase"})
    tool.run({"field": "Phase"})

    endpoints = [url.rsplit("/api/v2", 1)[-1] for url, _ in calls]
    assert endpoints.count("/stats/fieldValues") == 2
    assert endpoints.count("/stats/size") == 1
    assert endpoints.count("/stats/field/sizes") == 1


def test_a_failed_auxiliary_lookup_recovers_after_the_window(monkeypatch, calls):
    """...but it must heal by itself: remembering a failure forever would wedge
    the denominator off on a single blip."""
    down = {"value": True}

    def _fake_get(url, params=None, timeout=None, **kwargs):
        calls.append((url, params))
        if url.endswith("/stats/fieldValues"):
            return _FakeResponse(_PHASE_VALUES)
        if down["value"]:
            return _FakeResponse(None, status_code=503)
        if url.endswith("/stats/field/sizes"):
            return _FakeResponse(_LIST_FIELD_SIZES)
        return _FakeResponse(_STATS_SIZE)

    monkeypatch.setattr(requests, "get", _fake_get)
    tool = ClinicalTrialsTool(_load_config())
    # Expire the negative memo immediately rather than sleeping through it.
    monkeypatch.setattr(tool, "_AUX_FAILURE_TTL", 0)

    assert tool.run({"field": "Phase"})["data"]["total_studies_in_registry"] is None

    down["value"] = False
    recovered = tool.run({"field": "Phase"})["data"]
    assert recovered["total_studies_in_registry"] == _REGISTRY_TOTAL
    assert recovered["is_multi_valued"] is True
    assert recovered["duplicate_studies_count"] == _PHASE_DUPLICATES


# --------------------------------------------------------------------------
# Hermeticity
# --------------------------------------------------------------------------


def test_only_the_stubbed_getter_is_used(tool, calls):
    """Confirms the run above went through the three stubbed stats endpoints and
    nothing else -- with requests.request, requests.Session.request and
    socket.create_connection all set to raise, any other path would have failed."""
    tool.run({"field": "Phase"})

    assert [url.rsplit("/api/v2", 1)[-1] for url, _ in calls] == [
        "/stats/fieldValues",
        "/stats/size",
        "/stats/field/sizes",
    ]


def test_network_is_blocked_for_real(tool):
    """The guard fixture itself is asserted, so a future refactor that drops it
    cannot leave these tests quietly hitting ClinicalTrials.gov."""
    with pytest.raises(AssertionError, match="network access attempted"):
        socket.create_connection(("clinicaltrials.gov", 443))
    with pytest.raises(AssertionError, match="network access attempted"):
        requests.request("GET", "https://clinicaltrials.gov/api/v2/stats/size")
    with pytest.raises(AssertionError, match="network access attempted"):
        requests.Session().request(
            "GET", "https://clinicaltrials.gov/api/v2/stats/size"
        )
