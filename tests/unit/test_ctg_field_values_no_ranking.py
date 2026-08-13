"""Regression guards for Fix-R53-1: ClinicalTrials_get_field_values fabricated
the size of a facet it had not been given, and then used the fabrication to
certify that facet complete.

The defect, in four lines of `_run_field_values`:

    unique_values_count = field_obj.get("uniqueValuesCount")
    if not isinstance(unique_values_count, int):
        unique_values_count = len(all_values)      # <- invented
    ...
    upstream_truncated = len(all_values) < unique_values_count   # <- len < len

Whenever ClinicalTrials.gov did not publish `uniqueValuesCount`, the count
became the number of rows we happened to hold and the truncation test became
`len(all_values) < len(all_values)`, which is False for every input. A response
carrying no rows at all therefore reported `unique_values_count: 0`,
`values: []`, `truncated: false` -- a positive assertion that the field has no
distinct values.

This is not a corner case. Measured live against the whole
`/api/v2/stats/fieldValues` payload on 2026-08-13: of the 418 fields the API
exposes, 149 carry neither `topValues` nor `uniqueValuesCount`.

    type      fields   what the API sends INSTEAD of a ranking
    INTEGER      92    min / max / avg
    DATE         29    min / max / formats
    BOOLEAN      28    trueCount / falseCount
    STRING      214    (a real ranking; uniqueValuesCount always present)
    ENUM         55    (a real ranking; uniqueValuesCount always present)

All 269 STRING and ENUM fields carry `uniqueValuesCount`; the fallback never
fired for any field that had a ranking, and always fired for every field that
did not. So the invented number was wrong in exactly the cases it was reached.

Two distinct wrongs follow, and they need different fixes:

1. BOOLEAN -- the distribution EXISTS, under two scalar keys. `HasResults` is
   the case that matters: a caller asking how many registered studies have
   posted results was handed `values: []`. Live, the API sends
   trueCount 79,677 and falseCount 518,832, which sum to 598,509 -- exactly the
   registry total, with missingStudiesCount 0. That is a whole, exact facet
   that the tool discarded. It is now materialized as two rows.

2. INTEGER and DATE -- no ranking exists upstream and none can be synthesized
   (~600k distinct enrollment counts and start dates are not rankable). The
   honest report is a null count, an explicit truncation flag, and the range
   summary the API does send, which was previously parsed past and dropped.

The old prose made the contradiction plain in one sentence. For `HasResults`
the coverage_note simultaneously stated "leaving 598,509 studies represented",
"they partition the studies that record it", and "The rows sum to 0."

Hermetic in the same way as test_ctg_field_values_coverage.py: `requests.get`
is stubbed and `requests.request`, `requests.Session.request` and
`socket.create_connection` all raise, so a missed patch is a loud failure
rather than a silent live call.
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

_REGISTRY_TOTAL = 598509

# Verbatim shapes of live /api/v2/stats/fieldValues 200 responses, 2026-08-13.
# Note what is NOT in them: no `topValues`, no `uniqueValuesCount`.
_HAS_RESULTS_VALUES = [
    {
        "type": "BOOLEAN",
        "piece": "HasResults",
        "field": "hasResults",
        "missingStudiesCount": 0,
        "falseCount": 518832,
        "trueCount": 79677,
    }
]

_ENROLLMENT_VALUES = [
    {
        "type": "INTEGER",
        "piece": "EnrollmentCount",
        "field": "protocolSection.designModule.enrollmentInfo.count",
        "missingStudiesCount": 7131,
        "min": 0,
        "max": 188814085,
        "avg": 5505.268604497998,
    }
]

_START_DATE_VALUES = [
    {
        "type": "DATE",
        "piece": "StartDate",
        "field": "protocolSection.statusModule.startDateStruct.date",
        "missingStudiesCount": 5357,
        "min": "1900-01",
        "max": "2099-01-01",
        "formats": ["yyyy-MM", "yyyy-MM-dd"],
    }
]

# The control: an ENUM field with a real ranking, which must be unaffected.
_STUDY_TYPE_VALUES = [
    {
        "type": "ENUM",
        "piece": "StudyType",
        "field": "protocolSection.designModule.studyType",
        "missingStudiesCount": 982,
        "uniqueValuesCount": 3,
        "topValues": [
            {"value": "INTERVENTIONAL", "studiesCount": 454000},
            {"value": "OBSERVATIONAL", "studiesCount": 141692},
            {"value": "EXPANDED_ACCESS", "studiesCount": 1835},
        ],
    }
]

_LIST_FIELD_SIZES = [
    {"piece": "Phase", "field": "protocolSection.designModule.phases"},
    {"piece": "Condition", "field": "protocolSection.conditionsModule.conditions"},
]

_STATS_SIZE = {"totalStudies": _REGISTRY_TOTAL, "averageSizeBytes": 17275}

_VALUES_BY_FIELD = {
    "HasResults": _HAS_RESULTS_VALUES,
    "EnrollmentCount": _ENROLLMENT_VALUES,
    "StartDate": _START_DATE_VALUES,
    "StudyType": _STUDY_TYPE_VALUES,
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


def _data(tool, **arguments):
    result = tool.run(arguments)
    assert result["status"] == "success", result
    return result["data"]


# --------------------------------------------------------------------------
# BOOLEAN -- the facet exists and was thrown away
# --------------------------------------------------------------------------


def test_boolean_distribution_is_recovered_from_true_and_false_counts(tool):
    """The two scalars ARE the distribution; they must reach the caller as rows.

    Pre-fix this returned `values: []` -- the whole answer to "how many
    registered studies have posted results" discarded.
    """
    data = _data(tool, field="HasResults")

    assert data["values"] == [
        {"value": "false", "studies_count": 518832},
        {"value": "true", "studies_count": 79677},
    ]
    assert data["values_returned"] == 2


def test_boolean_facet_is_exact_and_reconciles_to_the_registry(tool):
    """A materialized boolean facet must survive the arithmetic it enables.

    518,832 + 79,677 = 598,509 = the registry total, with 0 studies missing, so
    `duplicate_studies_count` must come out at exactly 0 rather than being
    suppressed. Pre-fix the rows summed to 0 and the same subtraction produced
    a nonsense negative that was quietly discarded as None.
    """
    data = _data(tool, field="HasResults")

    assert sum(row["studies_count"] for row in data["values"]) == _REGISTRY_TOTAL
    assert data["studies_with_value"] == _REGISTRY_TOTAL
    assert data["duplicate_studies_count"] == 0
    assert "The rows sum to 598,509." in data["coverage_note"]


def test_boolean_facet_counts_two_values_and_is_not_truncated(tool):
    """unique_values_count 2, truncated False -- both now true statements.

    Pre-fix the same response said `unique_values_count: 0` and `truncated:
    false`: the count was invented from the empty row list, and the flag was
    derived from the invention, so "not truncated" was asserted about a facet
    the tool had never seen.
    """
    data = _data(tool, field="HasResults")

    assert data["unique_values_count"] == 2
    assert data["truncated"] is False
    assert data["value_summary"] is None


# --------------------------------------------------------------------------
# INTEGER and DATE -- no facet exists, and that must be said, not implied
# --------------------------------------------------------------------------


@pytest.mark.parametrize("field", ["EnrollmentCount", "StartDate"])
def test_unpublished_facet_size_is_null_not_zero(tool, field):
    """Null means unknown. Zero was a claim, and a false one.

    Pre-fix: `unique_values_count: 0` for both fields.
    """
    data = _data(tool, field=field)

    assert data["unique_values_count"] is None


@pytest.mark.parametrize("field", ["EnrollmentCount", "StartDate"])
def test_a_withheld_ranking_is_reported_as_truncation(tool, field):
    """Zero rows are fewer than the field's distinct values, so: truncated.

    This is the flag the whole defect turned on. Pre-fix it read `false` --
    `len([]) < len([])` -- telling a caller that an empty list was the complete
    set of values for a field 591,378 studies populate.
    """
    data = _data(tool, field=field)

    assert data["values"] == []
    assert data["truncated"] is True


def test_integer_range_summary_is_surfaced_instead_of_being_dropped(tool):
    """min/max/avg arrive in every INTEGER response and were parsed past."""
    data = _data(tool, field="EnrollmentCount")

    assert data["value_summary"] == {
        "minimum": 0,
        "maximum": 188814085,
        "average": 5505.268604497998,
    }


def test_date_range_summary_is_surfaced_instead_of_being_dropped(tool):
    """DATE sends formats where INTEGER sends an average; keep both."""
    data = _data(tool, field="StartDate")

    assert data["value_summary"] == {
        "minimum": "1900-01",
        "maximum": "2099-01-01",
        "date_formats": ["yyyy-MM", "yyyy-MM-dd"],
    }


@pytest.mark.parametrize("field", ["EnrollmentCount", "StartDate"])
def test_the_note_stops_asserting_things_about_rows_that_do_not_exist(tool, field):
    """The prose was not merely unhelpful for these fields -- it was false.

    Pre-fix, for StartDate, one note said all three of: "leaving 593,152
    studies represented", "they partition the studies that record it", and
    "The rows sum to 0."
    """
    note = _data(tool, field=field)["coverage_note"]

    assert "partition the studies that record it" not in note
    assert "The rows sum to 0" not in note
    assert "publishes NO per-value ranking" in note
    assert "NOT because no study records a value" in note


def test_the_note_still_reports_the_studies_excluded_from_the_facet(tool):
    """Suppressing the false half must not suppress the true half with it."""
    note = _data(tool, field="EnrollmentCount")["coverage_note"]

    assert "7,131" in note
    assert "591,378 studies represented" in note
    assert "minimum=0" in note


# --------------------------------------------------------------------------
# The fields that always had a ranking must be untouched
# --------------------------------------------------------------------------


def test_a_field_with_a_real_ranking_is_unaffected(tool):
    data = _data(tool, field="StudyType")

    assert data["unique_values_count"] == 3
    assert data["truncated"] is False
    assert data["value_summary"] is None
    assert data["values_returned"] == 3


def test_page_size_truncation_still_wins_over_an_unknown_facet_size(tool):
    """page_truncated is decidable even when the facet size is not."""
    data = _data(tool, field="StudyType", page_size=1)

    assert data["truncated"] is True
    assert data["values_returned"] == 1


# --------------------------------------------------------------------------
# The declared contract
# --------------------------------------------------------------------------


def test_config_declares_value_summary_and_nullable_counts():
    schema = _load_config()["return_schema"]["oneOf"][0]["properties"]

    assert "value_summary" in schema
    assert schema["value_summary"]["type"] == ["object", "null"]
    assert "null" in schema["unique_values_count"]["type"]
    assert "null" in schema["truncated"]["type"]
    # A caller must be told that null is not zero and not false.
    assert "never zero" in schema["unique_values_count"]["description"]
    assert "null is not false" in schema["truncated"]["description"]
