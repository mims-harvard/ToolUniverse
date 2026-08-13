"""A FAERS drug-name query must say how much of its answer is a different product.

Every FAERS drug-name lookup searches the union of FAERS_DRUG_NAME_FIELDS, and
two of those three fields are openFDA's own SPL annotation rather than the text
the reporter wrote. openFDA tags a drug entry with EVERY brand and generic name
registered for its active ingredient, so a brand-name query matches every
product sharing that ingredient.

The full measured range lives on ``FAERS_REPORTED_NAME_FIELD`` in
``openfda_adv_tool.py`` and is not restated here. The two drugs this module
drives are its extremes, measured live 2026-08-12 against ``meta.results.total``
("named" = patient.drug.medicinalproduct alone, "matched" = the union):

    CYANOKIT      238 named /  4,119 matched  -> 94.2% named something else
    OZEMPIC    66,161 named / 66,161 matched  ->  0.0%

CYANOKIT is the cyanide-poisoning antidote; hydroxocobalamin is also a routine
vitamin B12 supplement. Sampling the 3,881 CYANOKIT-matched reports that did not
name CYANOKIT returns B12 reports -- safetyreportid 10016092 is medicinalproduct
HYDROXOCOBALAMIN, drugindication MICROCYTIC ANAEMIA. Before this disclosure,
``FAERS_count_reactions_by_drug_event {"medicinalproduct": "CYANOKIT"}``
answered ACUTE KIDNEY INJURY 211 against total_reports_matching_query 4,119,
with nothing anywhere saying the denominator was mostly vitamin recipients.

The OZEMPIC row is why this is measured per call rather than warned about
statically: the share is a property of the drug, and for some drugs it is
exactly zero, so a fixed caveat would fire where there is nothing to caveat.

Pinned here: the two report counts are disclosed, the note appears only when the
query really did widen, the scope probe re-asks the SAME query with only the
drug name narrowed, and none of the pre-existing keys move. All openFDA HTTP is
mocked -- no network.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
import requests

import tooluniverse
from tooluniverse.openfda_adv_tool import (
    FAERS_REPORTED_NAME_FIELD,
    FDACountAdditiveReactionsTool,
    FDADrugAdverseEventTool,
)

pytestmark = pytest.mark.unit

DATA_DIR = Path(tooluniverse.__file__).parent / "data"

# The live CYANOKIT figures above.
MATCHED = 4119
NAMED = 238
ANNOTATION_ONLY = MATCHED - NAMED

FACET = [{"term": "ACUTE KIDNEY INJURY", "count": 211}]


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


def _run(arguments, matched=MATCHED, named=NAMED, named_fails=False, additive=False):
    """Drive a count tool, answering the two probes with different totals.

    The probes are told apart the way the tool builds them: the scope probe is
    the one whose drug clause carries only FAERS_REPORTED_NAME_FIELD.
    """
    urls = []

    def fake_get(url, **_kwargs):
        urls.append(url)
        return _Response({"results": FACET})

    def fake_total(_module, _method, url, **_kwargs):
        urls.append(url)
        is_scope_probe = "openfda.generic_name" not in url
        if is_scope_probe:
            if named_fails:
                raise requests.exceptions.RequestException("429 Too Many Requests")
            total = named
        else:
            total = matched
        return _Response({"meta": {"results": {"skip": 0, "limit": 0, "total": total}}})

    cls = FDACountAdditiveReactionsTool if additive else FDADrugAdverseEventTool
    name = (
        "FAERS_count_additive_adverse_reactions"
        if additive
        else "FAERS_count_reactions_by_drug_event"
    )
    tool = cls(_config(name), api_key=None)
    with (
        patch("tooluniverse.openfda_adv_tool.requests.get", side_effect=fake_get),
        patch(
            "tooluniverse.openfda_adv_tool.request_with_retry", side_effect=fake_total
        ),
    ):
        return tool.run(dict(arguments)), urls


# ---- 1. the widened case is disclosed, with both numbers ----


def test_a_brand_query_reports_how_many_reports_actually_named_the_brand():
    result, _ = _run({"medicinalproduct": "CYANOKIT"})

    assert result["total_reports_matching_query"] == MATCHED
    assert result["reports_naming_queried_drug"] == NAMED
    assert result["reports_matched_by_name_resolution_only"] == ANNOTATION_ONLY


def test_the_note_names_the_drug_the_share_and_what_the_rows_describe():
    note = _run({"medicinalproduct": "CYANOKIT"})[0]["drug_name_scope_note"]

    assert "'CYANOKIT'" in note
    assert f"{MATCHED:,}" in note and f"{NAMED:,}" in note
    assert f"{ANNOTATION_ONLY:,}" in note
    assert "94.2%" in note  # 3,881 / 4,119
    # The reader's next step is a rate off these rows, so the note has to say
    # whose population the rows describe.
    assert "active-ingredient population" in note
    assert "reports_naming_queried_drug" in note
    # And it must not promise a narrowing the tool cannot do.
    assert "cannot be narrowed" in note


# ---- 2. silent where it does not apply ----


def test_no_note_when_every_matched_report_named_the_drug():
    """OZEMPIC: 66,161 named of 66,161 matched. A static warning would fire here
    and be wrong, which is why the share is measured per call."""
    result, _ = _run({"medicinalproduct": "OZEMPIC"}, matched=66161, named=66161)

    assert result["reports_matched_by_name_resolution_only"] == 0
    assert "drug_name_scope_note" not in result


def test_a_failed_scope_probe_leaves_a_null_rather_than_breaking_the_call():
    result, _ = _run({"medicinalproduct": "CYANOKIT"}, named_fails=True)

    assert result["reports_naming_queried_drug"] is None
    assert "drug_name_scope_note" not in result
    # The facet and the denominator are untouched by the failure.
    assert result["results"] == [{"term": "ACUTE KIDNEY INJURY", "count": 211}]
    assert result["total_reports_matching_query"] == MATCHED


def test_no_scope_probe_at_all_when_no_drug_name_was_passed():
    """Costs nothing where it could not apply: two requests, not three."""
    result, urls = _run({"patientsex": "Female"})

    assert len(urls) == 2
    assert "reports_naming_queried_drug" not in result


# ---- 3. the probe asks the same question, narrowed only on the name ----


def test_the_scope_probe_keeps_every_other_filter_identical():
    _, urls = _run({"medicinalproduct": "CYANOKIT", "patientsex": "Female"})

    assert len(urls) == 3
    probes = [u for u in urls if "&count=" not in u]
    scope = next(u for u in probes if "openfda.generic_name" not in u)
    union = next(u for u in probes if u != scope)

    assert FAERS_REPORTED_NAME_FIELD in scope
    assert "openfda.brand_name" not in scope
    # Same non-name filter on both sides, or the two counts would not be
    # measuring the same population.
    assert "patient.patientsex:2" in scope and "patient.patientsex:2" in union


# ---- 4. the keys are declared, not just emitted ----


def test_every_disclosing_count_tool_declares_the_keys_it_emits():
    """An agent plans off `get_tool_info`, not off a payload it has not seen yet.

    A key that only appears at runtime is a key the planner cannot know to read,
    which for this one means reading `total_reports_matching_query` as the
    queried drug's population when it may be a different product's.
    """
    configs = json.loads((DATA_DIR / "fda_drug_adverse_event_tools.json").read_text())
    disclosing = [c for c in configs if c.get("disclose_denominator")]
    assert len(disclosing) == 18

    for config in disclosing:
        branch = next(
            b
            for b in config["return_schema"]["oneOf"]
            if "total_reports_matching_query" in b.get("properties", {})
        )
        for key in (
            "reports_naming_queried_drug",
            "reports_matched_by_name_resolution_only",
            "drug_name_scope_note",
        ):
            assert key in branch["properties"], (config["name"], key)
            # All three are conditional -- declaring them required would make the
            # schema wrong for the OZEMPIC case, where nothing widened.
            assert key not in branch.get("required", []), (config["name"], key)


# ---- 5. the multi-drug subclass discloses too ----


def test_the_multi_drug_tool_lists_every_queried_name_in_its_note():
    result, urls = _run(
        {"medicinalproducts": ["CYANOKIT", "IOSAT"]},
        matched=5514,
        named=244,
        additive=True,
    )

    assert len(urls) == 3
    assert result["reports_naming_queried_drug"] == 244
    assert result["reports_matched_by_name_resolution_only"] == 5270
    note = result["drug_name_scope_note"]
    assert "'CYANOKIT', 'IOSAT'" in note
