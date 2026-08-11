"""FAERS_count_death_related_by_drug must not invent a patient outcome or a rate.

Regression for Fix-R33, two problems in one response.

1. THE LABEL WAS INVENTED. The config mapped seriousnessdeath 2 -> "alive".
   `seriousnessdeath` is a report-level seriousness criterion, not a patient
   status field. openFDA's own field reference publishes exactly one sentence
   about it and no value enumeration at all:
       seriousnessdeath:
         description: "This value is `1` if the adverse event resulted in death,
                       and absent otherwise."
         possible_values:            # empty
     -- https://open.fda.gov/fields/drugevent.yaml (the machine-readable
        reference linked from https://open.fda.gov/apis/drug/event/searchable-fields/)
   A value of 2 IS returned by the live API but has NO published meaning; only
   the sibling top-level `serious` field publishes '2': "The adverse event did
   not result in any of the above". FAERS records patient outcome elsewhere, in
   patient.reaction.reactionoutcome, where '5': "Fatal". So "alive" asserted a
   clinical fact the data does not carry. This is the round's single authorised
   contract change: 1 -> "death criterion met", 2 -> "death criterion not met",
   with the undocumented status of 2 disclosed in coverage_note.

2. NO DENOMINATOR. Verified live before the fix:
     FAERS_count_death_related_by_drug {"medicinalproduct": "ACETAMINOPHEN"}
       -> [{"term": "alive", "count": 288391}, {"term": "death", "count": 125240}]
     https://api.fda.gov/drug/event.json?search=<same query>&limit=1
       -> meta.results.total = 799284
   The rows sum to 413,631 of 799,284 matching reports -- openFDA computes a
   `count=` facet only over records that populate the counted field, so the 48%
   of reports carrying no seriousnessdeath value are absent rather than bucketed.
   A reader computing 125,240/413,631 = 30.3% "case fatality" for acetaminophen
   is wrong by orders of magnitude.

The disclosure is additive and matches the vocabulary FAERS_stratify_by_demographics
already uses: total_reports_matching_query, stratified_report_count, coverage_note.

All assertions run against synthetic openFDA payloads -- no network.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import requests

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import tooluniverse  # noqa: E402
from tooluniverse.openfda_adv_tool import FDADrugAdverseEventTool  # noqa: E402

pytestmark = pytest.mark.unit

DATA_DIR = Path(tooluniverse.__file__).parent / "data"
TOOL_NAME = "FAERS_count_death_related_by_drug"

# Real acetaminophen facet: term is the integer code, rows sum to 413,631 while
# openFDA reports 799,284 matching reports for the same search.
DEATH_FACET = [{"term": 2, "count": 288391}, {"term": 1, "count": 125240}]
SUBSET = 413631
TRUE_TOTAL = 799284


def _config(name=TOOL_NAME):
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
    tool_name=TOOL_NAME, facet=None, total=TRUE_TOTAL, total_fails=False, **arguments
):
    """Drive the tool with the facet request and the total request mocked.

    The facet goes through `requests.get`; the denominator probe goes through the
    shared `request_with_retry` helper, so the two are patched separately.
    """
    facet_payload = {"results": DEATH_FACET if facet is None else facet}
    total_payload = {"meta": {"results": {"skip": 0, "limit": 0, "total": total}}}
    urls = []

    def fake_get(url, **_kwargs):
        urls.append(url)
        return _Response(facet_payload)

    def fake_total(_module, _method, url, **_kwargs):
        urls.append(url)
        if total_fails:
            raise requests.exceptions.RequestException("429 Too Many Requests")
        return _Response(total_payload)

    tool = FDADrugAdverseEventTool(_config(tool_name))
    with (
        patch("tooluniverse.openfda_adv_tool.requests.get", side_effect=fake_get),
        patch(
            "tooluniverse.openfda_adv_tool.request_with_retry", side_effect=fake_total
        ),
    ):
        result = tool.run({"medicinalproduct": "ACETAMINOPHEN", **arguments})
    return result, urls


# ---- 1. the relabel ----


def test_seriousnessdeath_2_is_no_longer_labelled_alive():
    """ "alive" asserted a patient status openFDA does not publish."""
    result, _ = _run()
    terms = [row["term"] for row in result["results"]]

    assert "alive" not in terms
    assert "death" not in terms  # bare "death" read as a patient outcome too
    assert terms == ["death criterion not met", "death criterion met"]


def test_both_labels_name_the_criterion_rather_than_the_patient():
    cfg = _config()
    mapping = cfg["fields"]["return_fields_mapping"]["seriousnessdeath"]

    assert mapping == {"1": "death criterion met", "2": "death criterion not met"}


def test_counts_are_carried_through_the_relabel_unchanged():
    """The contract change is the label only; the numbers must not move."""
    result, _ = _run()

    assert {row["term"]: row["count"] for row in result["results"]} == {
        "death criterion not met": 288391,
        "death criterion met": 125240,
    }


def test_config_documents_the_field_as_a_criterion_not_patient_status():
    cfg = _config()

    assert "not a patient-status field" in cfg["count_field_note"]
    assert "resulted in death" in cfg["count_field_note"]
    # Points the reader at the field that DOES carry patient outcome.
    assert "patient.reaction.reactionoutcome" in cfg["count_field_note"]
    assert "report-level seriousness criterion" in cfg["description"]
    assert "DO NOT SUPPORT A CASE-FATALITY RATE" in cfg["description"]


# ---- 2. the denominator ----


def test_subset_and_true_total_are_both_reported_and_distinguishable():
    result, _ = _run()

    assert result["stratified_report_count"] == SUBSET
    assert result["total_reports_matching_query"] == TRUE_TOTAL
    assert result["stratified_report_count"] != result["total_reports_matching_query"]
    assert result["stratified_report_count"] == sum(
        row["count"] for row in result["results"]
    )


def test_the_total_is_fetched_with_the_same_search_as_the_facet():
    """A different query would make the two figures incomparable."""
    _, urls = _run()

    facet_url = next(u for u in urls if "&count=" in u)
    total_url = next(u for u in urls if "&count=" not in u)
    assert facet_url.split("&count=")[0] == total_url.split("&limit=0")[0]
    # limit=0 returns meta.results.total without any report bodies.
    assert total_url.endswith("&limit=0")


def test_coverage_note_names_both_figures_the_fraction_and_the_rate_warning():
    note = _run()[0]["coverage_note"]

    assert f"{TRUE_TOTAL:,}" in note
    assert f"{SUBSET:,}" in note
    assert "51.8%" in note  # 413631 / 799284
    assert "seriousnessdeath" in note
    assert "do NOT support a case-fatality rate" in note
    assert "rather than bucketed" in note


def test_coverage_note_flags_that_openfda_publishes_no_meaning_for_value_2():
    """The label for 2 is an ICH convention, not something openFDA publishes."""
    note = _run()[0]["coverage_note"]

    assert "publishes no meaning at all for the value 2" in note
    assert "E2B" in note
    assert "https://open.fda.gov/fields/drugevent.yaml" in note


def test_a_failed_total_request_degrades_instead_of_erroring():
    result, _ = _run(total_fails=True)

    assert result["total_reports_matching_query"] is None
    assert result["stratified_report_count"] == SUBSET
    assert len(result["results"]) == 2
    assert "could not be retrieved" in result["coverage_note"]
    assert "LOWER BOUND" in result["coverage_note"]


def test_the_existing_envelope_keys_are_untouched():
    """Everything but the two labels is strictly additive."""
    result, _ = _run()

    assert result["result_count"] == 2
    assert result["limit"] == 100
    assert result["truncated"] is False
    assert "truncation_note" not in result


def test_return_schema_declares_the_new_keys():
    schema = _config()["return_schema"]["oneOf"][0]
    props = schema["properties"]

    assert props["total_reports_matching_query"]["type"] == ["integer", "null"]
    assert props["stratified_report_count"]["type"] == "integer"
    assert props["coverage_note"]["type"] == "string"
    for key in (
        "total_reports_matching_query",
        "stratified_report_count",
        "coverage_note",
    ):
        assert key in schema["required"]
    assert (
        "not patient" in props["results"]["items"]["properties"]["term"]["description"]
    )


# ---- the rest of the count family discloses too (Fix-R36) ----


def test_a_reaction_count_tool_discloses_as_well():
    """This test used to assert the opposite, on the grounds that a coverage
    fraction is meaningless for a field a report can carry many values of. The
    fraction is indeed not a coverage share there -- but withholding the
    denominator is what lets the reader invent a rate from the row sum, and a
    multi-valued facet sums ABOVE the report total rather than below, which is
    the more dangerous direction. Measured for vasopressin, 4,741 matching
    reports: patient.reaction.reactionoutcome sums to 5,514 (116%) and
    patient.drug.drugadministrationroute to 9,273 (196%). The wording for both
    directions is pinned in test_faers_count_facet_coverage.py."""
    result, urls = _run(
        tool_name="FAERS_count_reactions_by_drug_event",
        facet=[{"term": "DYSPNOEA", "count": 448}],
    )

    assert len(urls) == 2  # the facet plus the denominator probe
    assert result["total_reports_matching_query"] == TRUE_TOTAL
    assert result["stratified_report_count"] == 448
    assert "multi-valued" in result["coverage_note"]
    assert result["results"] == [{"term": "DYSPNOEA", "count": 448}]
