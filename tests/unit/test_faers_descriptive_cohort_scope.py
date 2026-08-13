"""Fix-R53-2: the cohort disclosure covered two operations out of six.

Round 52 added `cohort_scope` to `_calculate_disproportionality` and
`_compare_drugs` because a disproportionality signal computed over a
contaminated cohort is a safety INFERENCE that arrives with a confidence
interval. That is true, and it left four siblings in the same module building
the identical union cohort from the identical `_drug_clause` and publishing
their results with no disclosure whatsoever:

    _stratify_by_demographics    a demographic profile
    _filter_serious_events       serious-event counts and a reaction ranking
    _analyze_temporal_trends     a TREND VERDICT and a percent change
    _rollup_meddra_hierarchy     the drug's reaction profile

`_analyze_temporal_trends` is the one that should have been caught first: it
emits "Increasing" / "Decreasing" with a percent change, which is a verdict in
exactly the way an ROR is. Verified live 2026-08-13:

    FAERS_analyze_temporal_trends {"drug_name": "CYANOKIT"}
      -> trend "Increasing", percent_change 19900.0
      -> pre-fix: no cohort disclosure of any kind

CYANOKIT is a cyanide antidote with 4,119 reports in the union cohort, 238 of
which named it; the other 3,881 (94.2%) are hydroxocobalamin as vitamin B12
supplementation. So the trend published under the antidote's name was the
trend in B12 supplement reporting.

The union stays the analysed cohort for the same reason as on the inferential
path: no threshold separates brand contamination from a generic correctly
collecting its own brands (TOFACITINIB 93.0%, CYANOKIT 94.2%). What is pinned
here is that all four now measure and publish the split, that each says what
its own figures describe rather than borrowing the ROR wording, and that the
inferential path's behaviour is unchanged by the refactor that made this
shareable.

Offline: `_get_faers_count` and the HTTP layer are patched, so no openFDA
request is made.
"""

from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit

# Live CYANOKIT figures, 2026-08-13.
DRUG_TOTAL_UNION = 4119
NAMED_TOTAL = 238
MATCHED_ONLY = DRUG_TOTAL_UNION - NAMED_TOTAL  # 3881
SHARE = 94.2


def _tool():
    from tooluniverse.faers_analytics_tool import FAERSAnalyticsTool

    return FAERSAnalyticsTool({"name": "t", "type": "FAERSAnalyticsTool"})


class _FakeResponse:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _counts(named_total=NAMED_TOTAL, drug_total=DRUG_TOTAL_UNION):
    def fake_count(drug_name=None, adverse_event=None, reported_name_only=False):
        return named_total if reported_name_only else drug_total

    return fake_count


@pytest.fixture
def facets(monkeypatch):
    """One canned openFDA response per facet shape these operations request."""

    def fake_request(_module, _method, url, **kwargs):
        if "count=receivedate" in url:
            return _FakeResponse(
                {
                    "results": [
                        {"time": "20240101", "count": 100},
                        {"time": "20250101", "count": 200},
                    ]
                }
            )
        if "count=patient.patientsex" in url:
            return _FakeResponse(
                {"results": [{"term": 2, "count": 2199}, {"term": 1, "count": 1466}]}
            )
        if "limit=0" in url:
            return _FakeResponse({"meta": {"results": {"total": 312}}})
        return _FakeResponse(
            {"results": [{"term": "DEATH", "count": 50}, {"term": "COMA", "count": 9}]}
        )

    monkeypatch.setattr(
        "tooluniverse.faers_analytics_tool.request_with_retry", fake_request
    )


def _scope(operation, arguments, **kwargs):
    tool = _tool()
    with patch.object(tool, "_get_faers_count", side_effect=_counts(**kwargs)):
        result = getattr(tool, operation)(arguments)
    assert result.get("status") == "success", result
    payload = result.get("data", result)
    return payload["cohort_scope"]


_OPERATIONS = [
    ("_stratify_by_demographics", {"drug_name": "CYANOKIT", "stratify_by": "sex"}),
    ("_filter_serious_events", {"drug_name": "CYANOKIT", "seriousness_type": "death"}),
    ("_analyze_temporal_trends", {"drug_name": "CYANOKIT"}),
    ("_rollup_meddra_hierarchy", {"drug_name": "CYANOKIT"}),
]
_IDS = [name.lstrip("_") for name, _ in _OPERATIONS]


@pytest.mark.parametrize("operation,arguments", _OPERATIONS, ids=_IDS)
def test_every_descriptive_operation_publishes_the_split(facets, operation, arguments):
    """The key existed on two operations out of six. Pre-fix: KeyError here."""
    scope = _scope(operation, arguments)

    assert scope["reports_naming_queried_drug"] == NAMED_TOTAL
    assert scope["reports_matched_by_name_resolution_only"] == MATCHED_ONLY
    assert scope["percent_matched_by_name_resolution_only"] == SHARE


@pytest.mark.parametrize("operation,arguments", _OPERATIONS, ids=_IDS)
def test_the_note_describes_this_operations_own_output(facets, operation, arguments):
    """A stratification must not be told that its ROR is in question.

    The shared measurement is the point of the refactor; the shared PROSE would
    have been a regression, since only two of these six operations compute an
    ROR at all.
    """
    note = _scope(operation, arguments)["note"]

    assert "ROR/PRR/IC" not in note
    assert "'CYANOKIT'" in note
    assert "active-ingredient population" in note


def test_the_trend_verdict_is_named_as_what_the_split_qualifies(facets):
    """The sharpest case: a verdict, over a cohort that is 94.2% another drug."""
    result = _tool()
    with patch.object(result, "_get_faers_count", side_effect=_counts()):
        payload = result._analyze_temporal_trends({"drug_name": "CYANOKIT"})

    assert payload["trend_analysis"]["trend"] in {
        "Increasing",
        "Decreasing",
        "Stable",
        "Insufficient data",
    }
    note = payload["cohort_scope"]["note"]
    assert "The series and trend above describe" in note
    assert "is not the trend for 'CYANOKIT'" in note


def test_serious_events_says_which_cohort_it_measured(facets):
    """It measures the pre-seriousness cohort, so it must not imply otherwise.

    `serious:1` is orthogonal to which product a report named, so probing the
    narrower cohort would spend a request to answer the same question -- but a
    reader comparing 4,119 here against total_serious_events (312) above needs
    to be told they are different cohorts, not a contradiction.
    """
    note = _scope("_filter_serious_events", {"drug_name": "CYANOKIT"})["note"]

    assert "before the seriousness filter" in note
    assert f"{DRUG_TOTAL_UNION:,}" in note


@pytest.mark.parametrize("operation,arguments", _OPERATIONS, ids=_IDS)
def test_an_uncontaminated_cohort_gets_a_plain_statement(facets, operation, arguments):
    """OZEMPIC measures 0.0% non-naming; it must not be given a caveat."""
    scope = _scope(operation, arguments, named_total=DRUG_TOTAL_UNION)

    assert scope["reports_matched_by_name_resolution_only"] == 0
    assert "percent_matched_by_name_resolution_only" not in scope
    assert "as the product, so the metrics above are specific to it." in scope["note"]


@pytest.mark.parametrize("operation,arguments", _OPERATIONS, ids=_IDS)
def test_a_failed_probe_reads_as_unknown_not_zero(facets, operation, arguments):
    """The whole operation must survive a probe failure with its own output."""
    tool = _tool()

    def failing(drug_name=None, adverse_event=None, reported_name_only=False):
        return None if reported_name_only else DRUG_TOTAL_UNION

    with patch.object(tool, "_get_faers_count", side_effect=failing):
        result = getattr(tool, operation)(arguments)

    assert result["status"] == "success"
    scope = result.get("data", result)["cohort_scope"]
    assert scope["reports_naming_queried_drug"] is None
    assert "unknown, not as zero" in scope["note"]


@pytest.mark.parametrize("operation,arguments", _OPERATIONS, ids=_IDS)
def test_a_subset_larger_than_its_cohort_publishes_nothing(
    facets, operation, arguments
):
    """Only an openFDA refresh between the probes can produce this.

    Assertion is on the whole serialised result, not just on `cohort_scope`: a
    guard that returned after setting a key would still have shipped the
    impossible number.
    """
    import json

    impossible = DRUG_TOTAL_UNION + 1
    tool = _tool()
    with patch.object(
        tool, "_get_faers_count", side_effect=_counts(named_total=impossible)
    ):
        result = getattr(tool, operation)(arguments)

    assert result.get("data", result)["cohort_scope"] is None
    assert str(impossible) not in json.dumps(result)


def test_the_inferential_path_is_unchanged_by_the_refactor(facets):
    """`_cohort_scope` still offers the restricted ROR the descriptive ones cannot.

    The split moved into a shared helper; the second arm did not move with it,
    because there is no restricted form of a stratification or a trend.
    """
    tool = _tool()

    def fake_count(drug_name=None, adverse_event=None, reported_name_only=False):
        if reported_name_only:
            return 12 if adverse_event else NAMED_TOTAL
        if drug_name and adverse_event:
            return 50
        if drug_name:
            return DRUG_TOTAL_UNION
        if adverse_event:
            return 849880
        return 20692690

    with patch.object(tool, "_get_faers_count", side_effect=fake_count):
        result = tool._calculate_disproportionality(
            {"drug_name": "CYANOKIT", "adverse_event": "DEATH"}
        )

    scope = result["cohort_scope"]
    assert scope["percent_matched_by_name_resolution_only"] == SHARE
    assert scope["reported_name_only_analysis"]["ROR"]["value"] == 1.24
    assert "The ROR/PRR/IC above therefore describe" in scope["note"]


def test_config_declares_cohort_scope_where_the_schema_lists_properties():
    """Only stratify declares its keys; the other three declare a bare object."""
    import json
    from pathlib import Path

    path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "tooluniverse"
        / "data"
        / "faers_analytics_tools.json"
    )
    tools = {t["name"]: t for t in json.loads(path.read_text())}
    props = tools["FAERS_stratify_by_demographics"]["return_schema"]["properties"]

    assert props["cohort_scope"]["type"] == ["object", "null"]
    assert "never zero" in props["cohort_scope"]["description"]
