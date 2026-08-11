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

The multi-drug tools (``FDACountAdditiveReactionsTool``) were the last gap: they
hand-rolled the query, the URL and the request instead of extending the parent,
so ``_add_coverage_disclosure`` was never reached and the flag would have been a
silent no-op on their configs. Verified live before that fix,
``FAERS_count_additive_adverse_reactions(['VASOPRESSIN'], limit=100)`` returned
only results / result_count / limit / truncated / truncation_note, with the 100
rows summing to 18,379 against the 4,676 reports they were drawn from -- 393%,
undisclosed. They now override only ``_build_search_query``, so the OR clause
reaches the denominator probe too and the two figures stay comparable.

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
    FDACountAdditiveReactionsTool,
    FDADrugAdverseEventTool,
)
from tooluniverse.tool_registry import get_tool_registry

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

# The multi-drug tools build their own search -- `medicinalproducts` is a LIST
# OR-ed into one clause -- and it does NOT include the generic_name field the
# single-drug tools also search, so it has its own denominator. Measured live
# 2026-08 for search=(patient.drug.medicinalproduct:VASOPRESSIN):
#   meta.results.total                          4,676 matching reports
#   patient.reaction.reactionmeddrapt.exact    28,818 = 616% (first 999 rows)
#   patient.reaction.reactionoutcome            5,430 = 116%
#   patient.drug.drugadministrationroute.exact  9,169 = 196%
#   primarysource.reportercountry.exact         4,608 =  99%
#   serious                                     4,676 = 100%
#   occurcountry.exact                          3,888 =  83%
ADDITIVE_TOTAL = 4676
ADDITIVE_OUTCOME_FACET = [
    {"term": 6, "count": 2222},
    {"term": 5, "count": 1463},
    {"term": 1, "count": 986},
    {"term": 2, "count": 443},
    {"term": 3, "count": 284},
    {"term": 4, "count": 32},
]
ADDITIVE_OUTCOME_SUM = 5430  # 116% of 4,676 -- more "reports" than exist

SINGLE_DRUG = {"medicinalproduct": "vasopressin"}
MULTI_DRUG = {"medicinalproducts": ["VASOPRESSIN", "ASPIRIN"]}


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
    additive=False,
    facet_status=200,
    **arguments,
):
    """Drive a count tool with both openFDA requests mocked.

    The facet goes through ``requests.get``; the denominator probe goes through
    the shared ``request_with_retry`` helper, so the two are patched separately.
    ``disclose=False`` runs the same tool with the disclosure switched off, which
    is how the "nothing else moved" comparisons are made. ``additive=True``
    swaps in the multi-drug subclass, which takes a LIST of products -- the same
    mocks serve both, because the subclass overrides only the query builder.
    """
    urls = []

    def fake_get(url, **_kwargs):
        urls.append(url)
        payload = (
            {"error": {"code": "NOT_FOUND", "message": "No matches found!"}}
            if facet_status == 404
            else {"results": facet}
        )
        return _Response(payload, status_code=facet_status)

    def fake_total(_module, _method, url, **_kwargs):
        urls.append(url)
        if total_fails:
            raise requests.exceptions.RequestException("429 Too Many Requests")
        return _Response({"meta": {"results": {"skip": 0, "limit": 0, "total": total}}})

    cls = FDACountAdditiveReactionsTool if additive else FDADrugAdverseEventTool
    tool = cls(_config(tool_name), api_key=None)
    tool.disclose_denominator = disclose
    with (
        patch("tooluniverse.openfda_adv_tool.requests.get", side_effect=fake_get),
        patch(
            "tooluniverse.openfda_adv_tool.request_with_retry", side_effect=fake_total
        ),
    ):
        result = tool.run({**(MULTI_DRUG if additive else SINGLE_DRUG), **arguments})
    return result, urls


def _assert_same_search(urls):
    """Both requests searched the same query; only the count/limit differ.

    Returns ``(facet_url, total_url)`` so a caller can add its own assertions.
    A different search on either side would make the two figures incomparable.
    """
    assert len(urls) == 2
    facet_url = next(u for u in urls if "&count=" in u)
    total_url = next(u for u in urls if "&count=" not in u)
    assert facet_url.split("&count=")[0] == total_url.split("&limit=0")[0]
    assert total_url.endswith("&limit=0")
    return facet_url, total_url


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

    _assert_same_search(urls)


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


# ---- 5. the multi-drug tools go through the same disclosure ----


def _run_additive(tool_name, facet, total=ADDITIVE_TOTAL, **kwargs):
    return _run(tool_name, facet, total=total, additive=True, **kwargs)


def test_a_multi_drug_count_reaches_the_disclosure():
    """The gap this closes: `run` returned the envelope without disclosing.

    The wording of the note is the parent's and is pinned in section 1; what is
    new here is that a multi-drug call gets one at all, with the multi-drug
    denominator rather than a single product's.
    """
    result, _ = _run_additive(
        "FAERS_count_additive_reaction_outcomes", ADDITIVE_OUTCOME_FACET
    )

    assert result["stratified_report_count"] == ADDITIVE_OUTCOME_SUM
    assert result["total_reports_matching_query"] == ADDITIVE_TOTAL
    assert result["stratified_report_count"] > result["total_reports_matching_query"]
    assert "116.1%" in result["coverage_note"]  # 5,430 / 4,676
    # The rows themselves are untouched by the disclosure.
    assert result["results"][1] == {"term": "Fatal", "count": 1463}
    assert result["truncated"] is False


def test_the_multi_drug_denominator_searches_the_same_or_clause_as_the_facet():
    """This is why the subclass overrides `_build_search_query` rather than
    `run`: the OR clause has to reach `_fetch_query_total` as well."""
    _, urls = _run_additive(
        "FAERS_count_additive_reaction_outcomes", ADDITIVE_OUTCOME_FACET
    )

    facet_url, _ = _assert_same_search(urls)
    assert (
        "%28patient.drug.medicinalproduct:VASOPRESSIN"
        "+OR+patient.drug.medicinalproduct:ASPIRIN%29" in facet_url
    )


def test_a_multi_drug_filter_is_and_ed_onto_the_or_clause_in_both_requests():
    """The parent builds the filters; only the drug union is the subclass's."""
    _, urls = _run_additive(
        "FAERS_count_additive_reaction_outcomes",
        ADDITIVE_OUTCOME_FACET,
        patientsex="Female",
    )

    for url in urls:
        assert "%29+AND+patient.patientsex:2" in url


def test_a_multi_drug_query_matching_nothing_stays_an_empty_untruncated_envelope():
    """openFDA answers an unmatched search with 404; the parent reads it as zero."""
    result, _ = _run_additive(
        "FAERS_count_additive_reaction_outcomes", [], total=0, facet_status=404
    )

    assert result["results"] == []
    assert result["result_count"] == 0
    assert result["truncated"] is False
    assert "truncation_note" not in result
    assert result["total_reports_matching_query"] == 0
    assert result["stratified_report_count"] == 0
    assert "no facet coverage to report" in result["coverage_note"]


def test_a_missing_drug_list_is_rejected_before_any_request():
    tool = FDACountAdditiveReactionsTool(
        _config("FAERS_count_additive_reaction_outcomes")
    )
    with patch("tooluniverse.openfda_adv_tool.requests.get") as get:
        missing = tool.run({})
        wrong_type = tool.run({"medicinalproducts": "VASOPRESSIN"})

    assert missing == {
        "status": "error",
        "error": "`medicinalproducts` list is required.",
    }
    assert wrong_type == {
        "status": "error",
        "error": "`medicinalproducts` must be a list of drug names.",
    }
    get.assert_not_called()


# ---- 6. the whole family is consistent ----

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

# The same declaration for the multi-drug tools, whose counted field is
# `fields.return_fields[0]`. Ratios measured for medicinalproducts=['VASOPRESSIN']
# (4,676 reports) -- see ADDITIVE_TOTAL for the full table.
ADDITIVE_CARDINALITY = {
    "FAERS_count_additive_adverse_reactions": "per_reaction",  # 28,818 = 616%
    "FAERS_count_additive_event_reports_by_country": "per_report",  # 3,888 = 83%
    "FAERS_count_additive_reports_by_reporter_country": "per_report",  # 4,608 = 99%
    "FAERS_count_additive_seriousness_classification": "per_report",  # 4,676 = 100%
    "FAERS_count_additive_reaction_outcomes": "per_reaction",  # 5,430 = 116%
    "FAERS_count_additive_administration_routes": "per_drug",  # 9,169 = 196%
}

DECLARED_CARDINALITY = {
    "FDADrugAdverseEventTool": EXPECTED_CARDINALITY,
    "FDACountAdditiveReactionsTool": ADDITIVE_CARDINALITY,
}


def _all_configs():
    return json.loads((DATA_DIR / "fda_drug_adverse_event_tools.json").read_text())


def test_disclosing_types_covers_every_subclass_that_inherits_the_disclosure():
    """A new subclass must not slip past the checks below unnoticed.

    `run` -- and with it `_add_coverage_disclosure` -- is inherited, so every
    subclass of FDADrugAdverseEventTool honours the flag. Listing the types by
    hand is how the multi-drug tools went unchecked in the first place.
    """
    inheriting = {
        name
        for name, cls in get_tool_registry().items()
        if isinstance(cls, type) and issubclass(cls, FDADrugAdverseEventTool)
    }

    assert inheriting == set(DECLARED_CARDINALITY)


@pytest.mark.parametrize("tool_type", sorted(DECLARED_CARDINALITY))
def test_every_count_tool_discloses_its_denominator(tool_type):
    """The defect was inconsistency: some tools disclosed, most did not.

    The multi-drug tools were the last gap, and a silent one: they duplicated
    their parent's query building, URL building and request, so
    `_add_coverage_disclosure` was never reached and setting the flag on one of
    their configs did nothing at all.
    """
    expected = DECLARED_CARDINALITY[tool_type]
    tools = [c for c in _all_configs() if c["type"] == tool_type]

    assert {c["name"] for c in tools} == set(expected)
    for cfg in tools:
        assert cfg["disclose_denominator"] is True, cfg["name"]
        assert cfg["count_field_cardinality"] == expected[cfg["name"]], cfg["name"]


def test_every_disclosing_tool_declares_the_keys_in_its_return_schema():
    for cfg in _all_configs():
        if cfg["type"] not in DECLARED_CARDINALITY:
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
        if cfg["type"] not in DECLARED_CARDINALITY:
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
