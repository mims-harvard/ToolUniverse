"""A FAERS count facet must say what it does NOT sum to -- and in which direction.

openFDA's ``count=`` aggregation counts VALUES, not reports, and nothing in the
rows says so. The distortion runs both ways depending on the counted field, and
before Fix-R36 only ``FAERS_count_death_related_by_drug`` disclosed anything at
all. Verified live 2026-08 against
    search=(patient.drug.medicinalproduct:"vasopressin"
            OR patient.drug.openfda.generic_name:"vasopressin")
whose ``meta.results.total`` is 4,741 matching reports:

    FAERS_count_outcomes_by_drug_event  {"medicinalproduct": "vasopressin"}
      -> 6 rows summing to 5,514  = 116% of the 4,741 reports
         (Unknown 2,252 / Fatal 1,477 / Recovered 1,017 / Recovering 445 /
          Not recovered 291 / Recovered with sequelae 32)
    FAERS_count_drug_routes_by_event   {"medicinalproduct": "vasopressin"}
      -> 48 rows summing to 9,273  = 196%
    FAERS_count_country_by_drug_event  {"medicinalproduct": "vasopressin"}
      -> 58 rows summing to 3,949  =  83%

The first two exceed the report total because
``patient.reaction.reactionoutcome`` is recorded once per REACTION and
``patient.drug.drugadministrationroute`` once per DRUG, so one report lands in
several buckets. The third falls short because ``occurcountry`` is a per-report
field that many reports simply omit, and openFDA drops those reports from the
facet rather than bucketing them as unknown.

Each response carried only results / result_count / limit / truncated, so the
obvious next step -- case fatality = 1,477 / 5,514 = 27%, or 1,477 / 4,741 = 31%
-- mixed a per-reaction numerator with a per-report denominator and nothing in
the response objected.

Pinned here: the denominator is disclosed for the whole count family, the note
names the direction and the multi-valuedness, a failed denominator degrades to
null instead of erroring, and the existing rows/counts/flags are untouched.
All openFDA HTTP is mocked -- no network.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import requests

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import tooluniverse  # noqa: E402
from tooluniverse.openfda_adv_tool import (  # noqa: E402
    COUNT_FIELD_UNITS,
    FDADrugAdverseEventTool,
)

pytestmark = pytest.mark.unit

DATA_DIR = Path(tooluniverse.__file__).parent / "data"
VASOPRESSIN_TOTAL = 4741

# The real facet for FAERS_count_outcomes_by_drug_event, as openFDA returns it:
# terms are the raw reactionoutcome codes, mapped to labels by the tool.
OUTCOME_FACET = [
    {"term": 6, "count": 2252},
    {"term": 5, "count": 1477},
    {"term": 1, "count": 1017},
    {"term": 2, "count": 445},
    {"term": 3, "count": 291},
    {"term": 4, "count": 32},
]
OUTCOME_SUM = 5514  # 116% of 4,741 -- more "reports" than exist

# The six most-reported of the 58 real occurcountry rows (the full facet sums to
# 3,949, i.e. 83% of the 4,741 reports).
COUNTRY_FACET = [
    {"term": "US", "count": 2633},
    {"term": "CA", "count": 453},
    {"term": "JP", "count": 127},
    {"term": "DE", "count": 96},
    {"term": "GB", "count": 81},
    {"term": "EU", "count": 68},
]
COUNTRY_SUM = 3458


def _config(name):
    configs = json.loads((DATA_DIR / "fda_drug_adverse_event_tools.json").read_text())
    return next(c for c in configs if c["name"] == name)


class _Response:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _run(
    tool_name,
    facet,
    total=VASOPRESSIN_TOTAL,
    total_fails=False,
    disclose=True,
    **arguments,
):
    """Drive a count tool with both openFDA requests mocked.

    The facet goes through ``requests.get``; the denominator probe goes through
    the shared ``request_with_retry`` helper, so the two are patched separately.
    ``disclose=False`` runs the same tool with the disclosure switched off, which
    is how the "nothing else moved" comparisons are made.
    """
    urls = []

    def fake_get(url, **_kwargs):
        urls.append(url)
        return _Response({"results": facet})

    def fake_total(_module, _method, url, **_kwargs):
        urls.append(url)
        if total_fails:
            raise requests.exceptions.RequestException("429 Too Many Requests")
        return _Response({"meta": {"results": {"skip": 0, "limit": 0, "total": total}}})

    tool = FDADrugAdverseEventTool(_config(tool_name), api_key=None)
    tool.disclose_denominator = disclose
    with (
        patch("tooluniverse.openfda_adv_tool.requests.get", side_effect=fake_get),
        patch(
            "tooluniverse.openfda_adv_tool.request_with_retry", side_effect=fake_total
        ),
    ):
        result = tool.run({"medicinalproduct": "vasopressin", **arguments})
    return result, urls


# ---- 1. the facet sums ABOVE the report total ----


def test_outcome_facet_discloses_that_it_counts_more_than_the_reports():
    result, _ = _run("FAERS_count_outcomes_by_drug_event", OUTCOME_FACET)

    assert result["stratified_report_count"] == OUTCOME_SUM
    assert result["total_reports_matching_query"] == VASOPRESSIN_TOTAL
    # The whole point: the facet sums to MORE than the reports it describes.
    assert result["stratified_report_count"] > result["total_reports_matching_query"]


def test_the_note_names_the_multi_valued_field_and_the_direction():
    note = _run("FAERS_count_outcomes_by_drug_event", OUTCOME_FACET)[0]["coverage_note"]

    assert "multi-valued" in note
    assert "patient.reaction.reactionoutcome" in note
    assert "once per reaction, not once per report" in note
    assert "MORE than the number of matching reports" in note
    assert "DOUBLE-COUNT" in note
    assert "116.3%" in note  # 5,514 / 4,741
    assert f"{VASOPRESSIN_TOTAL:,}" in note and f"{OUTCOME_SUM:,}" in note


def test_the_note_forbids_the_row_sum_as_a_denominator_and_offers_the_right_one():
    """1,477 Fatal / 5,514 is the rate this note exists to prevent."""
    note = _run("FAERS_count_outcomes_by_drug_event", OUTCOME_FACET)[0]["coverage_note"]

    assert "do NOT use it as a denominator" in note
    assert "do NOT divide one row by it to obtain a rate" in note
    assert "use total_reports_matching_query" in note


def test_the_route_facet_discloses_the_same_way_for_a_per_drug_field():
    """patient.drug.drugadministrationroute: 9,273 = 196% of the 4,741 reports."""
    facet = [{"term": "042", "count": 9273}]
    note = _run("FAERS_count_drug_routes_by_event", facet)[0]["coverage_note"]

    assert "patient.drug.drugadministrationroute" in note
    assert "once per drug, not once per report" in note
    assert "MORE than the number of matching reports" in note
    # The `.exact` query suffix is not part of the field's identity.
    assert ".exact" not in note


# ---- 2. the facet sums BELOW the report total ----


def test_country_facet_discloses_that_reports_are_excluded_from_it():
    result, _ = _run("FAERS_count_country_by_drug_event", COUNTRY_FACET)
    note = result["coverage_note"]

    assert result["stratified_report_count"] == COUNTRY_SUM
    assert result["total_reports_matching_query"] == VASOPRESSIN_TOTAL
    assert result["stratified_report_count"] < result["total_reports_matching_query"]
    assert "occurcountry" in note
    assert "EXCLUDED from the rows entirely rather than bucketed as unknown" in note
    assert "72.9%" in note  # 3,458 / 4,741
    # A per-report field does not double-count, and saying so is the difference
    # between the two directions.
    assert "holds at most one value per report" in note
    assert "multi-valued" not in note


def test_a_multi_valued_field_below_the_total_states_both_effects():
    """Both distortions can apply at once, and the reader must know it.

    A reaction facet whose rows sum under the report total is under it because
    reports missing the field are dropped -- not because the rows stopped
    double-counting.
    """
    facet = [{"term": "DYSPNOEA", "count": 448}]
    note = _run("FAERS_count_reactions_by_drug_event", facet)[0]["coverage_note"]

    assert "pull in opposite directions" in note
    assert "multi-valued" in note
    assert "DOUBLE-COUNT" in note
    assert "EXCLUDED from the facet" in note
    assert "must not be used as a denominator" in note


# ---- 3. the denominator fails soft ----


def test_a_failed_denominator_yields_null_and_a_note_not_an_error():
    result, _ = _run(
        "FAERS_count_outcomes_by_drug_event", OUTCOME_FACET, total_fails=True
    )

    assert result["total_reports_matching_query"] is None
    assert result["stratified_report_count"] == OUTCOME_SUM
    assert result["result_count"] == 6  # the rows still came back
    assert "status" not in result
    note = result["coverage_note"]
    assert "could not be retrieved" in note
    assert "may exceed the number of matching reports" in note
    assert "Do not use it as a denominator" in note
    assert "FDA_API_KEY" in note


def test_a_failed_denominator_on_a_per_report_field_says_lower_bound():
    result, _ = _run(
        "FAERS_count_country_by_drug_event", COUNTRY_FACET, total_fails=True
    )

    assert result["total_reports_matching_query"] is None
    assert "LOWER BOUND" in result["coverage_note"]


def test_the_denominator_uses_the_same_search_as_the_facet_and_limit_zero():
    """A different query would make the two figures incomparable."""
    _, urls = _run("FAERS_count_outcomes_by_drug_event", OUTCOME_FACET)

    assert len(urls) == 2
    facet_url = next(u for u in urls if "&count=" in u)
    total_url = next(u for u in urls if "&count=" not in u)
    assert facet_url.split("&count=")[0] == total_url.split("&limit=0")[0]
    assert total_url.endswith("&limit=0")


# ---- 4. strictly additive: nothing that existed moved ----


def test_rows_counts_limit_and_truncated_are_identical_with_and_without_disclosure():
    with_disclosure, _ = _run("FAERS_count_outcomes_by_drug_event", OUTCOME_FACET)
    without, _ = _run(
        "FAERS_count_outcomes_by_drug_event", OUTCOME_FACET, disclose=False
    )

    for key in ("results", "result_count", "limit", "truncated"):
        assert with_disclosure[key] == without[key], key
    # And the rows themselves are the real, unchanged facet.
    assert with_disclosure["results"][1] == {"term": "Fatal", "count": 1477}
    assert with_disclosure["result_count"] == 6
    assert with_disclosure["limit"] == 100
    assert with_disclosure["truncated"] is False
    assert set(with_disclosure) - set(without) == {
        "stratified_report_count",
        "total_reports_matching_query",
        "coverage_note",
    }


def test_a_truncated_ranking_says_the_sum_covers_only_the_rows_shown():
    result, _ = _run("FAERS_count_outcomes_by_drug_event", OUTCOME_FACET, limit=3)

    assert result["truncated"] is True
    assert result["result_count"] == 3
    assert result["stratified_report_count"] == 2252 + 1477 + 1017
    assert "sums only the rows shown" in result["coverage_note"]
    assert "truncation_note" in result


def test_a_query_matching_nothing_says_so_instead_of_dividing_zero_by_zero():
    """openFDA answers an unmatched search with 404, which the probe reads as a
    true zero; "0, 0.0% of 0" would read as a malfunction."""
    result, _ = _run("FAERS_count_outcomes_by_drug_event", [], total=0)

    assert result["results"] == []
    assert result["total_reports_matching_query"] == 0
    assert result["stratified_report_count"] == 0
    assert "no facet coverage to report" in result["coverage_note"]
    assert "%" not in result["coverage_note"]


def test_an_api_failure_still_surfaces_as_an_error_not_a_disclosure():
    """The facet failing must not be dressed up in a coverage note."""
    tool = FDADrugAdverseEventTool(_config("FAERS_count_outcomes_by_drug_event"))
    with patch(
        "tooluniverse.openfda_adv_tool.requests.get",
        side_effect=requests.exceptions.ConnectionError("boom"),
    ):
        out = tool.run({"medicinalproduct": "vasopressin"})

    assert isinstance(out, list)
    assert "API request failed" in out[0]["error"]


# ---- 5. the whole family is consistent ----

# The cardinality each count tool declares, i.e. how many values of the counted
# field ONE report can carry. Pinned so a field nested under patient.reaction[]
# or patient.drug[] cannot be quietly relabelled report-level, which would make
# the note deny double-counting that is really happening. Ratios measured for
# vasopressin (4,741 reports) are given as the evidence for each.
EXPECTED_CARDINALITY = {
    "FAERS_count_reactions_by_drug_event": "per_reaction",  # 29,070 = 613%
    "FAERS_count_drugs_by_drug_event": "per_drug",  # 71,874 = 1516%
    "FAERS_count_country_by_drug_event": "per_report",  # 3,949 = 83%
    "FAERS_count_reportercountry_by_drug_event": "per_report",  # 4,673 = 99%
    "FAERS_count_seriousness_by_drug_event": "per_report",  # 4,741 = 100%
    "FAERS_count_outcomes_by_drug_event": "per_reaction",  # 5,514 = 116%
    "FAERS_count_drug_routes_by_event": "per_drug",  # 9,273 = 196%
    "FAERS_count_patient_age_distribution": "per_report",  # 906 = 19%
    "FAERS_count_death_related_by_drug": "per_report",  # report-level flag
    "FAERS_count_indications_by_drug": "per_drug",  # 21,895 = 462%
    "FAERS_count_drug_characterization": "per_drug",  # 8,266 = 174%
    "FAERS_count_reporter_qualification": "per_report",  # 4,603 = 97%
}


def _all_configs():
    return json.loads((DATA_DIR / "fda_drug_adverse_event_tools.json").read_text())


def test_every_single_drug_count_tool_discloses_its_denominator():
    """The defect was inconsistency: some tools disclosed, most did not."""
    tools = [c for c in _all_configs() if c["type"] == "FDADrugAdverseEventTool"]

    assert {c["name"] for c in tools} == set(EXPECTED_CARDINALITY)
    for cfg in tools:
        assert cfg["disclose_denominator"] is True, cfg["name"]
        assert cfg["count_field_cardinality"] == EXPECTED_CARDINALITY[cfg["name"]], cfg[
            "name"
        ]


def test_the_multi_drug_tools_do_not_claim_a_disclosure_they_cannot_make():
    """FDACountAdditiveReactionsTool builds its own query and never calls
    `_add_coverage_disclosure`, so the flag would be a silent no-op there."""
    additive = [
        c for c in _all_configs() if c["type"] == "FDACountAdditiveReactionsTool"
    ]

    assert additive
    for cfg in additive:
        assert "disclose_denominator" not in cfg, cfg["name"]
        schema = cfg["return_schema"]["oneOf"][0]
        assert "coverage_note" not in schema["properties"], cfg["name"]


def test_every_disclosing_tool_declares_the_keys_in_its_return_schema():
    for cfg in _all_configs():
        if cfg["type"] != "FDADrugAdverseEventTool":
            continue
        schema = cfg["return_schema"]["oneOf"][0]
        props = schema["properties"]
        assert props["total_reports_matching_query"]["type"] == ["integer", "null"]
        assert props["stratified_report_count"]["type"] == "integer"
        assert props["coverage_note"]["type"] == "string"
        for key in (
            "total_reports_matching_query",
            "stratified_report_count",
            "coverage_note",
        ):
            assert key in schema["required"], (cfg["name"], key)


def test_every_disclosing_description_states_the_direction():
    for cfg in _all_configs():
        if cfg["type"] != "FDADrugAdverseEventTool":
            continue
        description = cfg["description"]
        assert "total_reports_matching_query" in description, cfg["name"]
        if cfg["count_field_cardinality"] in COUNT_FIELD_UNITS:
            assert "NOT once per report" in description, cfg["name"]
            assert "MORE than the number of matching reports" in description, cfg[
                "name"
            ]
        elif cfg["name"] == "FAERS_count_death_related_by_drug":
            # Predates the shared wording and spells the same fact out its own
            # way; left as it shipped rather than churned for uniformity.
            assert "absent rather than bucketed" in description
        else:
            assert "at most one value per report" in description, cfg["name"]
