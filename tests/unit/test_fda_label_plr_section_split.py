"""Offline regression tests for the PLR-vs-legacy label-section split.

Defect this covers
------------------
An FDA label files its safety content under different section names depending on
the FORMAT it was written in, not on the drug:

* "PLR" labels (Physician Labeling Rule, 2006 onward) use ``warnings_and_cautions``
  and usually carry no ``warnings`` section at all;
* legacy / OTC-monograph labels use ``warnings`` / ``precautions`` and usually
  carry no ``warnings_and_cautions``.

``FDA_get_warnings_by_drug_name`` queries only ``warnings`` and ``boxed_warning``,
so for every PLR label it returned ``status: success`` with both sections null.
Read literally that says "this drug has no warnings". Live evidence, CLI::

    $ python -m tooluniverse.cli run FDA_get_warnings_by_drug_name \\
        '{"drug_name":"Giapreza"}'
    status: success   meta.total: 1
    warnings: None    boxed_warning: None

GIAPREZA is angiotensin II, a vasopressor whose defining safety issue is
thrombosis. Upstream the warning is plainly there, under the other key::

    $ curl -G 'https://api.fda.gov/drug/label.json' \\
        --data-urlencode 'search=openfda.brand_name:"GIAPREZA"' --data 'limit=1'
    'warnings' in record:       False
    'boxed_warning' in record:  False
    warning-ish keys present:   ['warnings_and_cautions']
    "5. WARNINGS AND PRECAUTIONS There is a potential for venous and arterial
     thrombotic and thromboembolic events in patients who receive GIAPREZA.
     Use concurrent venous thromboembolism (VTE) prophylaxis. ... (13% vs. 5%)"

and the sibling tool retrieved it fine::

    $ python -m tooluniverse.cli run FDA_get_warnings_and_cautions_by_drug_name \\
        '{"drug_name":"GIAPREZA"}'
    -> the full WARNINGS AND PRECAUTIONS text

Scale, measured against openFDA drug/label on 2026-08-11 with
``search=_exists_:<field>&limit=0``::

    total labels                                    261,639
    _exists_:warnings                               208,073
    _exists_:warnings_and_cautions                   46,925
    warnings_and_cautions AND NOT warnings           43,486   <-- always-null
    warnings AND NOT warnings_and_cautions          204,634

So the null answer is not an edge case: 43,486 labels (16.6% of the corpus, and
the vintage every recently-approved drug belongs to) can never answer this tool.

Pinned properties
-----------------
1. requested section null + sibling populated -> sibling attached under its OWN
   key, named in ``related_sections_present``, and a ``section_note`` that names
   the sibling tool;
2. the requested keys are never overwritten with sibling content (provenance);
3. requested section populated -> output byte-identical to before, no new keys;
4. one of several requested sections populated -> no annotation (the OZEMPIC
   shape: ``warnings`` null but ``boxed_warning`` present);
5. annotation cannot resurrect a record that would otherwise be dropped;
6. an exact-name query that NOT_FOUNDs purely because of the ``_exists_`` guard
   is retried against the sibling sections (the KEYTRUDA shape) instead of
   reporting "No matches found!";
7. tools that do not request a safety section are untouched.

Everything mocks the HTTP layer -- no network.
"""

import sys
import types
from unittest.mock import patch

import pytest

from tooluniverse.openfda_tool import (
    LABEL_SECTION_SIBLINGS,
    LABEL_SECTION_TOOLS,
    FDADrugLabelTool,
)

NOT_FOUND = {"error": {"code": "NOT_FOUND", "message": "No matches found!"}}

_DRUG_LIST_MODULE = "tooluniverse.data.fda_drugs_with_brand_generic_names_for_tool"


@pytest.fixture
def tiny_drug_list(monkeypatch):
    """Stub the 6 MB / 129k-line closest-name table.

    The last NOT_FOUND fallback stage scans every brand and generic name in that
    table. Loading and walking it under coverage instrumentation takes minutes,
    which is unrelated to anything these tests assert.
    """
    stub = types.ModuleType(_DRUG_LIST_MODULE)
    stub.drug_list = [{"brand_name": "GIAPREZA", "generic_name": "ANGIOTENSIN II"}]
    monkeypatch.setitem(sys.modules, _DRUG_LIST_MODULE, stub)
    return stub


GIAPREZA_WARNINGS_AND_CAUTIONS = (
    "5. WARNINGS AND PRECAUTIONS There is a potential for venous and arterial "
    "thrombotic and thromboembolic events in patients who receive GIAPREZA. "
    "Use concurrent venous thromboembolism (VTE) prophylaxis."
)


def _config(name, return_fields):
    return {
        "name": name,
        "description": name,
        "type": "FDADrugLabel",
        "parameter": {
            "type": "object",
            "properties": {"drug_name": {"type": "string"}},
            "required": ["drug_name"],
        },
        "fields": {
            "search_fields": {
                "drug_name": ["openfda.brand_name", "openfda.generic_name"]
            },
            "return_fields": return_fields,
        },
    }


WARNINGS_CONFIG = _config(
    "FDA_get_warnings_by_drug_name", ["warnings", "boxed_warning"]
)
INDICATIONS_CONFIG = _config(
    "FDA_get_indications_by_drug_name", ["indications_and_usage"]
)


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload
        self.status_code = 200

    def json(self):
        return self._payload


def _payload(records, total=None):
    return {
        "meta": {
            "results": {
                "skip": 0,
                "limit": 100,
                "total": len(records) if total is None else total,
            }
        },
        "results": records,
    }


def _plr_label():
    """A PLR-format label: no `warnings`, no `boxed_warning`, content elsewhere."""
    return {
        "openfda": {"brand_name": ["Giapreza"], "generic_name": ["ANGIOTENSIN II"]},
        "warnings_and_cautions": [GIAPREZA_WARNINGS_AND_CAUTIONS],
        "spl_product_data_elements": ["Giapreza angiotensin II ANGIOTENSIN II"],
    }


def _run(config, records, drug_name="Giapreza"):
    """Serve `records` on the first query -- the exact-name path, no fallbacks."""
    tool = FDADrugLabelTool(config)
    with patch(
        "tooluniverse.openfda_tool.requests.get",
        return_value=_FakeResponse(_payload(records)),
    ):
        return tool.run({"drug_name": drug_name, "limit": 10})


# --------------------------------------------------------------------------
# 1 + 2: the Giapreza shape -- null section, sibling surfaced, provenance kept
# --------------------------------------------------------------------------


def test_null_warnings_surface_the_sibling_section_that_carries_them():
    result = _run(WARNINGS_CONFIG, [_plr_label()])

    row = result["results"][0]
    # The requested sections still report exactly what openFDA reported.
    assert row["warnings"] is None
    assert row["boxed_warning"] is None
    # ...but the content the label DOES carry is now visible, under its own name.
    assert row["warnings_and_cautions"] == [GIAPREZA_WARNINGS_AND_CAUTIONS]
    assert row["related_sections_present"] == ["warnings_and_cautions"]


def test_section_note_names_the_sibling_section_and_the_sibling_tool():
    result = _run(WARNINGS_CONFIG, [_plr_label()])

    note = result["section_note"]
    assert "warnings_and_cautions" in note
    assert "FDA_get_warnings_and_cautions_by_drug_name" in note
    # The whole point: the response must not read as an all-clear.
    assert "PLR" in note
    assert "no warnings" in note


def test_sibling_content_is_never_rewritten_into_the_requested_key():
    """`warnings` must not silently become warnings_and_cautions text."""
    result = _run(WARNINGS_CONFIG, [_plr_label()])

    row = result["results"][0]
    assert row["warnings"] is None
    assert row["warnings"] != row["warnings_and_cautions"]


def test_section_note_is_separate_from_the_broadened_match_note():
    """`note` describes how the QUERY was weakened; the two must not collide.

    Emitting the section explanation under `note` would have overwritten the
    fuzzy-match warning that tells the caller to check the returned drug name.
    """
    records = [_plr_label()]

    def fake_get(url, *args, **kwargs):
        # Only the closest-spelling stage (which searches
        # spl_product_data_elements without any _exists_ guard) succeeds.
        if "spl_product_data_elements" in url:
            return _FakeResponse(_payload(records))
        return _FakeResponse(NOT_FOUND)

    tool = FDADrugLabelTool(WARNINGS_CONFIG)
    with patch("tooluniverse.openfda_tool.requests.get", side_effect=fake_get):
        result = tool.run({"drug_name": "Giaprezaa", "limit": 10})

    # `note` still carries the broadened-match warning...
    assert "Giaprezaa" in result["note"]
    assert "matched exactly" in result["note"] or "closest-spelling" in result["note"]
    # ...and the section explanation arrives alongside it, not instead of it.
    assert "warnings_and_cautions" in result["section_note"]


# --------------------------------------------------------------------------
# 3 + 4: the working path is untouched
# --------------------------------------------------------------------------


def test_populated_warnings_return_exactly_what_they_did_before():
    """A legacy label with real `warnings` gains no keys and no note."""
    legacy = {
        "openfda": {"brand_name": ["Low Dose Aspirin"], "generic_name": ["ASPIRIN"]},
        "warnings": ["Warnings Reye's syndrome: Children and teenagers ..."],
        "spl_product_data_elements": ["Low Dose Aspirin Aspirin ASPIRIN"],
    }
    result = _run(WARNINGS_CONFIG, [legacy], drug_name="Aspirin")

    assert result["results"] == [
        {
            "openfda.brand_name": ["Low Dose Aspirin"],
            "openfda.generic_name": ["ASPIRIN"],
            "warnings": ["Warnings Reye's syndrome: Children and teenagers ..."],
            "boxed_warning": None,
            "spl_product_data_elements": ["Low Dose Aspirin Aspirin ASPIRIN"],
        }
    ]
    assert "section_note" not in result
    assert "related_sections_present" not in result["results"][0]


def test_one_populated_requested_section_suppresses_the_annotation():
    """The OZEMPIC shape: `warnings` null but `boxed_warning` present.

    Nothing is missing here -- the caller already has warning content in a
    requested field -- so no sibling is fetched and no note is emitted.
    """
    ozempic = {
        "openfda": {"brand_name": ["OZEMPIC"], "generic_name": ["SEMAGLUTIDE"]},
        "boxed_warning": ["WARNING: RISK OF THYROID C-CELL TUMORS"],
        "warnings_and_cautions": ["5 WARNINGS AND PRECAUTIONS Pancreatitis ..."],
        "spl_product_data_elements": ["OZEMPIC semaglutide"],
    }
    result = _run(WARNINGS_CONFIG, [ozempic], drug_name="OZEMPIC")

    row = result["results"][0]
    assert row["boxed_warning"] == ["WARNING: RISK OF THYROID C-CELL TUMORS"]
    assert "warnings_and_cautions" not in row
    assert "related_sections_present" not in row
    assert "section_note" not in result


def test_tools_that_request_no_safety_section_are_untouched():
    label = dict(_plr_label())
    label["indications_and_usage"] = ["1. INDICATIONS AND USAGE GIAPREZA increases ..."]
    result = _run(INDICATIONS_CONFIG, [label])

    row = result["results"][0]
    assert set(row) == {
        "openfda.brand_name",
        "openfda.generic_name",
        "indications_and_usage",
        "spl_product_data_elements",
    }
    assert "section_note" not in result


# --------------------------------------------------------------------------
# 5: the annotation can never invent a row
# --------------------------------------------------------------------------


def test_annotation_never_resurrects_an_otherwise_empty_record():
    """A record with no openfda names and no requested content stays dropped.

    Sibling annotation runs AFTER the "did we extract anything?" test, exactly
    like the `spl_product_data_elements` identity fallback.
    """
    empty_but_has_sibling = {
        "openfda": {},
        "warnings_and_cautions": ["Some warnings and cautions text."],
        "spl_product_data_elements": ["Some product"],
    }
    result = _run(WARNINGS_CONFIG, [empty_but_has_sibling, _plr_label()])

    assert result["result_count"] == 1
    assert result["results"][0]["openfda.brand_name"] == ["Giapreza"]


# --------------------------------------------------------------------------
# 6: NOT_FOUND caused only by the _exists_ guard
# --------------------------------------------------------------------------


def test_exact_name_not_found_only_because_of_the_exists_guard_is_retried():
    """The KEYTRUDA shape.

    KEYTRUDA has neither `warnings` nor `boxed_warning`, so
    `(_exists_:warnings+OR+_exists_:boxed_warning)` filtered the label out
    entirely and the tool answered "No matches found!" for a drug with pages of
    warnings. Retrying with the sibling sections finds it.
    """
    keytruda = {
        "openfda": {"brand_name": ["KEYTRUDA"], "generic_name": ["PEMBROLIZUMAB"]},
        "warnings_and_cautions": ["5 WARNINGS AND PRECAUTIONS Immune-Mediated ..."],
        "spl_product_data_elements": ["KEYTRUDA pembrolizumab"],
    }
    seen = []

    def fake_get(url, *args, **kwargs):
        seen.append(url)
        if "warnings_and_cautions" in url:
            return _FakeResponse(_payload([keytruda]))
        return _FakeResponse(NOT_FOUND)

    tool = FDADrugLabelTool(WARNINGS_CONFIG)
    with patch("tooluniverse.openfda_tool.requests.get", side_effect=fake_get):
        result = tool.run({"drug_name": "KEYTRUDA", "limit": 10})

    assert result.get("status") != "error"
    row = result["results"][0]
    assert row["warnings"] is None
    assert row["warnings_and_cautions"] == [
        "5 WARNINGS AND PRECAUTIONS Immune-Mediated ..."
    ]
    assert "FDA_get_warnings_and_cautions_by_drug_name" in result["section_note"]
    # The drug-name clause is preserved -- only the _exists_ group is swapped.
    retry = next(u for u in seen if "warnings_and_cautions" in u)
    assert "KEYTRUDA" in retry


def test_a_genuinely_absent_drug_still_reports_not_found(tiny_drug_list):
    tool = FDADrugLabelTool(WARNINGS_CONFIG)
    with patch(
        "tooluniverse.openfda_tool.requests.get",
        return_value=_FakeResponse(NOT_FOUND),
    ):
        result = tool.run({"drug_name": "Zzzqxwvfake", "limit": 1})

    assert result["status"] == "error"
    assert result["error"]["code"] == "NOT_FOUND"
    assert result["results"] == []


def test_not_found_suggestion_never_names_a_nonexistent_openfda_field(tiny_drug_list):
    """`warnings_and_precautions` is the printed heading, not an openFDA field.

    It is absent from openFDA's searchable-field list for drug/label and
    `search=_exists_:warnings_and_precautions` returns NOT_FOUND, so the old
    suggestion pointed callers at a query that could never work.
    """
    tool = FDADrugLabelTool(WARNINGS_CONFIG)
    with patch(
        "tooluniverse.openfda_tool.requests.get",
        return_value=_FakeResponse(NOT_FOUND),
    ):
        result = tool.run({"drug_name": "Zzzqxwvfake", "limit": 1})

    suggestion = result["suggestion"]
    assert "warnings_and_precautions" not in suggestion
    assert "warnings_and_cautions" in suggestion
    assert "FDA_get_warnings_and_cautions_by_drug_name" in suggestion


# --------------------------------------------------------------------------
# The sibling map itself
# --------------------------------------------------------------------------


def test_every_sibling_section_names_a_real_tool():
    for section, siblings in LABEL_SECTION_SIBLINGS.items():
        assert section in LABEL_SECTION_TOOLS, section
        for sibling in siblings:
            assert sibling in LABEL_SECTION_TOOLS, (section, sibling)
        assert section not in siblings, section
