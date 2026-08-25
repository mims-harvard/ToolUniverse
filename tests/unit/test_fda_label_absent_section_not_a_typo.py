"""Offline regression tests: an absent label SECTION is not a misspelled NAME.

Defect this covers
------------------
``FDA_get_pharmacogenomics_info_by_drug_name`` returned rows of pure nulls, an
inflated ``meta.total``, and a factually false note -- for exactly the drugs a
pharmacogenomics user is most likely to ask about. Live evidence, CLI::

    $ python -m tooluniverse.cli run FDA_get_pharmacogenomics_info_by_drug_name \\
        '{"drug_name":"codeine","limit":20}'
    meta.total: 533   rows: 2   rows with non-null pharmacogenomics: 0
    note: "No drug named 'codeine' was found; showing the closest-spelling
           candidate(s) (CODEINE, CODEINUM) instead ..."

Two independent faults, both visible in that one output.

**The number is impossible.** Measured against openFDA on 2026-08-11::

    search=_exists_:pharmacogenomics&limit=0                         ->   524
    search=openfda.generic_name:"codeine"
           +AND+_exists_:pharmacogenomics&limit=0                    ->     0
    search=spl_product_data_elements:"ABACAVIR"&limit=0              ->    66

524 is the size of the ENTIRE candidate corpus -- every label in openFDA that
has a ``pharmacogenomics`` section at all. A hit count for "codeine labels
having a pharmacogenomics section" cannot exceed it, and 533 does. The true
answer is the second line: zero.

**Root cause.** Tracing the outbound URLs for ``abacavir`` showed four requests.
The first three all carry ``+AND+(_exists_:pharmacogenomics)`` and all NOT_FOUND.
The fourth -- the closest-spelling stage -- was::

    search=(spl_product_data_elements:"ABACAVIR")

with the guard gone entirely. That answers a different question ("labels whose
product-data blob mentions ABACAVIR"), so its 66 hits became ``meta.total`` and
every row necessarily carried ``pharmacogenomics: null``.

**The note is separately false.** It asserted "No drug named 'abacavir' was
found" and offered "ABACAVIR" as a *closest-spelling candidate* -- the identical
string in different case. 23 abacavir labels exist by generic_name alone. The
note blamed a missing *section* on a misspelled *name*, sending the reader to
fix a spelling that was never wrong.

**Why it matters clinically.** Codeine (CYP2D6 ultrarapid metabolisers) and
abacavir (HLA-B*57:01) are the two textbook pharmacogenomics drugs, both
carrying FDA boxed warnings driven by genotype. That information lives in the
boxed warning, not in SPL section 12.5, so openFDA's ``pharmacogenomics`` field
is genuinely empty for them. A reader who got empty rows plus a note blaming
their spelling would reasonably conclude there is no pharmacogenomic concern --
the exact opposite of the truth.

Pinned properties
-----------------
1. the closest-spelling stage keeps the ``_exists_:<section>`` guard, so no
   response can report a relaxed query's hit count as the guarded one's;
2. name matches but no label has the section -> honest empty result, and the
   suggestion says the spelling is fine and names the sections the drug DOES
   have, via the existing ``LABEL_SECTION_TOOLS`` map;
3. that suggestion never tells the caller to check their spelling;
4. a genuine misspelling still gets rescued, and is still called a misspelling;
5. a candidate differing from the input only by CASE is never presented as a
   spelling suggestion;
6. a drug that truly does not exist still gets spelling advice, and is never
   told its spelling is correct;
7. the working path -- section present -- is untouched and issues no probe.

Everything mocks the HTTP layer -- no network.
"""

import sys
import types
import urllib.parse
from unittest.mock import patch

import pytest

from tooluniverse.openfda_tool import FDADrugLabelTool

NOT_FOUND = {"error": {"code": "NOT_FOUND", "message": "No matches found!"}}

_DRUG_LIST_MODULE = "tooluniverse.data.fda_drugs_with_brand_generic_names_for_tool"


@pytest.fixture
def tiny_drug_list(monkeypatch):
    """Stub the 6 MB / 129k-line closest-name table.

    The closest-spelling stage scans every brand and generic name in it; loading
    and walking that under coverage instrumentation takes minutes and is
    unrelated to anything asserted here.
    """
    stub = types.ModuleType(_DRUG_LIST_MODULE)
    stub.drug_list = [
        {"brand_name": "ZIAGEN", "generic_name": "ABACAVIR"},
        {"brand_name": "MOTRIN", "generic_name": "IBUPROFEN"},
    ]
    monkeypatch.setitem(sys.modules, _DRUG_LIST_MODULE, stub)
    return stub


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


PGX_CONFIG = _config("FDA_get_pharmacogenomics_info_by_drug_name", ["pharmacogenomics"])
CONTRA_CONFIG = _config("FDA_get_contraindications_by_drug_name", ["contraindications"])


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload
        self.status_code = 200

    def json(self):
        return self._payload


def _payload(records, total):
    return {
        "meta": {"results": {"skip": 0, "limit": 100, "total": total}},
        "results": records,
    }


def _abacavir_label():
    """A real-shaped abacavir label: HLA-B*57:01 is in the boxed warning.

    openFDA has no `pharmacogenomics` section for it -- which is precisely why
    the guarded query NOT_FOUNDs while the drug plainly exists.
    """
    return {
        "openfda": {"brand_name": ["ZIAGEN"], "generic_name": ["ABACAVIR SULFATE"]},
        "boxed_warning": [
            "WARNING: HYPERSENSITIVITY REACTIONS ... patients who carry "
            + "the HLA-B*57:01 allele are at high risk ..."
        ],
        "warnings_and_cautions": ["5 WARNINGS AND PRECAUTIONS Hypersensitivity ..."],
        "spl_product_data_elements": ["ZIAGEN abacavir sulfate ABACAVIR SULFATE"],
    }


def _serve(section, records, name_total, section_total=0):
    """Model openFDA: the `_exists_:<section>` guard decides the answer.

    `section_total` is the upstream hit count for queries that DO carry the
    guard (0 means every guarded query NOT_FOUNDs); `name_total` is the count
    for the unguarded name query.
    """
    seen = []

    def fake_get(url, *args, **kwargs):
        seen.append(urllib.parse.unquote(url))
        if f"_exists_:{section}" in seen[-1] and not section_total:
            return _FakeResponse(NOT_FOUND)
        total = section_total if f"_exists_:{section}" in seen[-1] else name_total
        return _FakeResponse(_payload(records, total))

    return fake_get, seen


# --------------------------------------------------------------------------
# 1: the closest-spelling stage must stay guarded
# --------------------------------------------------------------------------


def test_closest_spelling_stage_keeps_the_exists_guard(tiny_drug_list):
    """No outbound query may drop the section the caller asked for.

    This is the whole defect in one assertion: the stage that searched
    `spl_product_data_elements:"ABACAVIR"` with no guard is what produced 66
    null rows and a `meta.total` drawn from a corpus nobody asked about.
    """
    fake_get, seen = _serve("pharmacogenomics", [_abacavir_label()], name_total=23)

    tool = FDADrugLabelTool(PGX_CONFIG)
    with patch("tooluniverse.openfda_tool.requests.get", side_effect=fake_get):
        tool.run({"drug_name": "abacavir", "limit": 20})

    closest = [u for u in seen if 'spl_product_data_elements:"ABACAVIR"' in u]
    assert closest, seen
    for url in closest:
        assert "_exists_:pharmacogenomics" in url


def test_meta_total_never_reports_a_relaxed_querys_hit_count(tiny_drug_list):
    """533 > 524, the size of the whole pharmacogenomics corpus. It cannot stand."""
    fake_get, _ = _serve("pharmacogenomics", [_abacavir_label()], name_total=533)

    tool = FDADrugLabelTool(PGX_CONFIG)
    with patch("tooluniverse.openfda_tool.requests.get", side_effect=fake_get):
        result = tool.run({"drug_name": "abacavir", "limit": 20})

    assert result["meta"]["total"] == 0
    assert result["results"] == []
    assert result["result_count"] == 0


# --------------------------------------------------------------------------
# 2 + 3: name fine, section absent -> say so, and point somewhere useful
# --------------------------------------------------------------------------


def test_absent_section_is_reported_as_absent_not_as_a_typo(tiny_drug_list):
    fake_get, _ = _serve("pharmacogenomics", [_abacavir_label()], name_total=23)

    tool = FDADrugLabelTool(PGX_CONFIG)
    with patch("tooluniverse.openfda_tool.requests.get", side_effect=fake_get):
        result = tool.run({"drug_name": "abacavir", "limit": 20})

    suggestion = result["suggestion"]
    # The name was never the problem, and the count of matching labels proves it.
    assert "spelled correctly" in suggestion
    assert "23" in suggestion
    # The missing thing is named for what it is.
    assert "pharmacogenomics" in suggestion
    assert "SECTION" in suggestion
    # ...and the reader is warned off the dangerous reading.
    assert "NOT evidence" in suggestion


def test_absent_section_suggestion_never_blames_the_spelling(tiny_drug_list):
    """The old note sent readers to fix a spelling that was never wrong."""
    fake_get, _ = _serve("pharmacogenomics", [_abacavir_label()], name_total=23)

    tool = FDADrugLabelTool(PGX_CONFIG)
    with patch("tooluniverse.openfda_tool.requests.get", side_effect=fake_get):
        result = tool.run({"drug_name": "abacavir", "limit": 20})

    suggestion = result["suggestion"]
    assert "checking spelling" not in suggestion
    assert "No drug named" not in suggestion
    assert "closest-spelling" not in suggestion
    assert result.get("note") is None


def test_absent_section_names_the_sections_the_drug_does_have(tiny_drug_list):
    """Turn the dead end into a next step, using the existing tool map.

    Abacavir's HLA-B*57:01 genotype warning really is on the label -- in the
    boxed warning. Naming that tool is the difference between "no
    pharmacogenomic concern" and the truth.
    """
    fake_get, _ = _serve("pharmacogenomics", [_abacavir_label()], name_total=23)

    tool = FDADrugLabelTool(PGX_CONFIG)
    with patch("tooluniverse.openfda_tool.requests.get", side_effect=fake_get):
        result = tool.run({"drug_name": "abacavir", "limit": 20})

    suggestion = result["suggestion"]
    assert "boxed_warning" in suggestion
    assert "FDA_get_boxed_warning_info_by_drug_name" in suggestion
    assert "FDA_get_warnings_and_cautions_by_drug_name" in suggestion


# --------------------------------------------------------------------------
# 4 + 5: real misspellings still work, case differences are not misspellings
# --------------------------------------------------------------------------


def test_a_genuine_misspelling_is_still_rescued_and_still_called_one(tiny_drug_list):
    """`ibuprofin` -> IBUPROFEN differs by more than case, so the note is true."""
    label = {
        "openfda": {"brand_name": ["MOTRIN"], "generic_name": ["IBUPROFEN"]},
        "contraindications": ["4 CONTRAINDICATIONS Known hypersensitivity ..."],
        "spl_product_data_elements": ["MOTRIN ibuprofen IBUPROFEN"],
    }
    seen = []

    def fake_get(url, *args, **kwargs):
        seen.append(urllib.parse.unquote(url))
        # Only the corrected spelling matches anything.
        if 'spl_product_data_elements:"IBUPROFEN"' in seen[-1]:
            return _FakeResponse(_payload([label], 697))
        return _FakeResponse(NOT_FOUND)

    tool = FDADrugLabelTool(CONTRA_CONFIG)
    with patch("tooluniverse.openfda_tool.requests.get", side_effect=fake_get):
        result = tool.run({"drug_name": "ibuprofin", "limit": 20})

    assert result.get("status") != "error"
    assert "closest-spelling" in result["note"]
    assert "IBUPROFEN" in result["note"]
    # ...and the rescue query still constrained on the requested section, so the
    # rows can actually answer the question that was asked.
    rescue = next(u for u in seen if 'spl_product_data_elements:"IBUPROFEN"' in u)
    assert "_exists_:contraindications" in rescue
    assert result["results"][0]["contraindications"] is not None


def test_a_case_only_difference_is_never_called_a_spelling_candidate(tiny_drug_list):
    """ "abacavir" vs "ABACAVIR" is the same word. Offering it as a correction
    is how the old note managed to claim a correctly-spelled drug was not found.
    """
    label = dict(_abacavir_label())
    label["pharmacogenomics"] = ["12.5 PHARMACOGENOMICS HLA-B*57:01 ..."]
    seen = []

    def fake_get(url, *args, **kwargs):
        seen.append(urllib.parse.unquote(url))
        # Only the product-data-elements stage matches -- the openfda name
        # fields are empty on this label, as they are for many repackagers.
        if 'spl_product_data_elements:"ABACAVIR"' in seen[-1]:
            return _FakeResponse(_payload([label], 66))
        return _FakeResponse(NOT_FOUND)

    tool = FDADrugLabelTool(PGX_CONFIG)
    with patch("tooluniverse.openfda_tool.requests.get", side_effect=fake_get):
        result = tool.run({"drug_name": "abacavir", "limit": 20})

    note = result["note"]
    assert "No drug named" not in note
    assert "closest-spelling" not in note
    # It says what actually happened instead: an ingredient-field match.
    assert "product data elements" in note


# --------------------------------------------------------------------------
# 6: a drug that really does not exist
# --------------------------------------------------------------------------


def test_a_nonexistent_drug_is_never_told_its_spelling_is_correct(tiny_drug_list):
    tool = FDADrugLabelTool(PGX_CONFIG)
    with patch(
        "tooluniverse.openfda_tool.requests.get",
        return_value=_FakeResponse(NOT_FOUND),
    ):
        result = tool.run({"drug_name": "zzqqxwv", "limit": 5})

    suggestion = result["suggestion"]
    assert result["status"] == "error"
    assert "spelled correctly" not in suggestion
    assert "checking spelling" in suggestion


def test_suggestion_does_not_invent_siblings_for_a_section_that_has_none(
    tiny_drug_list,
):
    """`pharmacogenomics` has no sibling section.

    The old code fell back to a hardcoded ["contraindications",
    "warnings_and_cautions"] and wrapped it in the PLR-vs-legacy explanation --
    a fact about the WARNINGS family, asserted of an unrelated section.
    """
    tool = FDADrugLabelTool(PGX_CONFIG)
    with patch(
        "tooluniverse.openfda_tool.requests.get",
        return_value=_FakeResponse(NOT_FOUND),
    ):
        result = tool.run({"drug_name": "zzqqxwv", "limit": 5})

    suggestion = result["suggestion"]
    assert "Try a related section" not in suggestion
    assert "PLR" not in suggestion
    # It still points somewhere real.
    assert "FDA_get_boxed_warning_info_by_drug_name" in suggestion


# --------------------------------------------------------------------------
# 7: the working path is untouched
# --------------------------------------------------------------------------


def test_a_drug_that_has_the_section_is_unaffected_and_issues_no_probe():
    """The warfarin shape: first query succeeds, nothing else runs."""
    warfarin = {
        "openfda": {"brand_name": ["COUMADIN"], "generic_name": ["WARFARIN SODIUM"]},
        "pharmacogenomics": ["12.5 PHARMACOGENOMICS CYP2C9 and VKORC1 ..."],
        "spl_product_data_elements": ["COUMADIN warfarin sodium"],
    }
    seen = []

    def fake_get(url, *args, **kwargs):
        seen.append(url)
        return _FakeResponse(_payload([warfarin], 12))

    tool = FDADrugLabelTool(PGX_CONFIG)
    with patch("tooluniverse.openfda_tool.requests.get", side_effect=fake_get):
        result = tool.run({"drug_name": "warfarin", "limit": 20})

    assert len(seen) == 1
    assert result["meta"]["total"] == 12
    assert result["results"][0]["pharmacogenomics"] == [
        "12.5 PHARMACOGENOMICS CYP2C9 and VKORC1 ..."
    ]
    assert result.get("note") is None
    assert "suggestion" not in result
