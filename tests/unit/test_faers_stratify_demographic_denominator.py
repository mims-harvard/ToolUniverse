"""FAERS_stratify_by_demographics must distinguish the subset from the total.

Regression for Fix-R33. The tool summed the openFDA `count=` facet rows and
emitted that sum as `total_reports`. openFDA computes a count facet ONLY over
records that populate the counted field, so reports missing
patient.patientagegroup / patient.patientsex / occurcountry are dropped from the
facet rather than bucketed as unknown. FAERS records demographics on a minority
of reports, so the sum is the stratifiable subset, not the total.

Verified live before the fix:
  FAERS_stratify_by_demographics {"drug": "ondansetron", "stratify_by": "age"}
    -> "total_reports": 25424, groups summing to exactly 25424
  https://api.fda.gov/drug/event.json?search=...ondansetron...&limit=0
    -> meta.results.total = 136216
A clinician reading `total_reports` would have understated the drug's report
count more than fivefold.

The fix is additive: `total_reports` keeps its old value and the percentages are
unchanged (a share of the stratifiable subset is the right denominator for a
stratification). The subset gains the self-describing name
`stratified_report_count`, the true total arrives as
`total_reports_matching_query` from a second request on the SAME base_query, and
`coverage_note` names both figures plus the coverage fraction.

All assertions run against synthetic openFDA payloads -- no network.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import tooluniverse  # noqa: E402
from tooluniverse.faers_analytics_tool import FAERSAnalyticsTool  # noqa: E402

pytestmark = pytest.mark.unit

DATA_DIR = Path(tooluniverse.__file__).parent / "data"

# Real ondansetron age-group facet shape: term is the integer code, and the rows
# sum to 25,424 while openFDA reports 136,216 matching reports overall.
AGE_FACET = [
    {"term": 5, "count": 13112},
    {"term": 6, "count": 10235},
    {"term": 3, "count": 840},
    {"term": 4, "count": 758},
    {"term": 1, "count": 331},
    {"term": 2, "count": 148},
]
SUBSET = 25424
TRUE_TOTAL = 136216


class _Response:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _run(facet=None, total=TRUE_TOTAL, total_fails=False, **arguments):
    """Drive the tool with the facet request and the total request mocked."""
    facet_payload = {"results": AGE_FACET if facet is None else facet}
    total_payload = {"meta": {"results": {"skip": 0, "limit": 0, "total": total}}}
    seen_urls = []

    def fake_request(_module, _method, url, **_kwargs):
        seen_urls.append(url)
        if "&limit=0" in url:
            if total_fails:
                raise RuntimeError("openFDA 429 Too Many Requests")
            return _Response(total_payload)
        return _Response(facet_payload)

    tool = FAERSAnalyticsTool(
        {"name": "FAERS_stratify_by_demographics", "parameter": {}, "fields": {}}
    )
    with patch(
        "tooluniverse.faers_analytics_tool.request_with_retry", side_effect=fake_request
    ):
        result = tool.run(
            {
                "operation": "stratify_by_demographics",
                "drug": "ondansetron",
                **arguments,
            }
        )
    assert result["status"] == "success", result
    return result["data"], seen_urls


def test_subset_and_true_total_are_both_reported_and_distinguishable():
    data, _ = _run(stratify_by="age")

    assert data["stratified_report_count"] == SUBSET
    assert data["total_reports_matching_query"] == TRUE_TOTAL
    assert data["stratified_report_count"] != data["total_reports_matching_query"]
    assert data["stratified_report_count"] == sum(
        row["count"] for row in data["stratification"]
    )


def test_legacy_total_reports_keeps_its_old_value():
    """Additive: a caller reading total_reports sees exactly what it saw before."""
    data, _ = _run(stratify_by="age")

    assert data["total_reports"] == SUBSET
    assert data["total_reports"] == data["stratified_report_count"]


def test_percentages_are_unchanged_shares_of_the_subset():
    data, _ = _run(stratify_by="age")

    by_group = {row["group"]: row for row in data["stratification"]}
    assert by_group["Adult"]["percentage"] == 51.57
    assert by_group["Elderly"]["percentage"] == 40.26
    for row in data["stratification"]:
        assert row["percentage"] == pytest.approx(row["count"] / SUBSET * 100, abs=0.01)


def test_the_total_is_fetched_with_the_same_base_query_as_the_facet():
    """A different query would make the two figures incomparable."""
    _, urls = _run(stratify_by="age")

    facet_url = next(u for u in urls if "&count=" in u)
    total_url = next(u for u in urls if "&limit=0" in u)
    assert facet_url.split("&count=")[0] == total_url.split("&limit=0")[0]
    assert "patient.patientagegroup" in facet_url


def test_coverage_note_names_both_figures_and_the_fraction():
    note = _run(stratify_by="age")[0]["coverage_note"]

    assert f"{TRUE_TOTAL:,}" in note
    assert f"{SUBSET:,}" in note
    assert "18.7%" in note  # 25424 / 136216
    assert "patient.patientagegroup" in note
    assert "backward compatibility" in note


def test_a_failed_total_request_degrades_instead_of_erroring():
    data, _ = _run(stratify_by="age", total_fails=True)

    assert data["total_reports_matching_query"] is None
    assert data["stratified_report_count"] == SUBSET
    assert data["total_reports"] == SUBSET
    assert len(data["stratification"]) == len(AGE_FACET)
    assert "could not be retrieved" in data["coverage_note"]
    assert "LOWER BOUND" in data["coverage_note"]


def test_sex_stratification_reports_its_own_partial_coverage():
    """Coverage differs per field, so the total must be fetched, not assumed."""
    data, urls = _run(
        facet=[{"term": 2, "count": 60000}, {"term": 1, "count": 30000}],
        stratify_by="sex",
    )

    assert data["stratified_report_count"] == 90000
    assert data["total_reports_matching_query"] == TRUE_TOTAL
    assert [row["group"] for row in data["stratification"]] == ["Female", "Male"]
    assert "patient.patientsex" in next(u for u in urls if "&count=" in u)


def test_config_documents_the_denominator_caveat_and_the_new_keys():
    configs = json.loads((DATA_DIR / "faers_analytics_tools.json").read_text())
    cfg = next(c for c in configs if c["name"] == "FAERS_stratify_by_demographics")

    assert "total_reports_matching_query" in cfg["description"]
    assert "stratified_report_count" in cfg["description"]

    props = cfg["return_schema"]["properties"]
    assert props["total_reports_matching_query"]["type"] == ["integer", "null"]
    assert props["stratified_report_count"]["type"] == "integer"
    assert props["coverage_note"]["type"] == "string"
    assert "NOT the drug's report count" in props["total_reports"]["description"]
