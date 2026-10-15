"""FDALabelTool must find labels openFDA never linked, without returning excipient matches.

Found in a real Codex session: `FDA_get_drug_label` answered "No FDA label found"
for osimertinib and for Tagrisso, although the TAGRISSO label is on openFDA. That
label has no `openfda` block (177,901 labels are like it, measured with
`_missing_:openfda`), so the `openfda.generic_name` / `openfda.brand_name`
searches cannot reach it. Its only name field is `spl_product_data_elements`,
which also lists every inactive ingredient.

All tests here mock the HTTP layer -- no network. The product texts are copied
from live openFDA records.
"""

from unittest.mock import patch

import pytest

from tooluniverse.fda_label_tool import FDALabelTool, _names_product_itself

TAGRISSO = "TAGRISSO osimertinib OSIMERTINIB OSIMERTINIB MANNITOL MICROCRYSTALLINE CELLULOSE"
# All lower case, and two strength blocks, so case and raw counts both mislead.
AMBIEN = (
    "Ambien zolpidem tartrate zolpidem tartrate zolpidem hypromelloses lactose "
    "magnesium stearate cellulose, microcrystalline polyethylene glycols titanium "
    "dioxide FD&C Red No. 40 polysorbate 80 pink CAPSULE-SHAPED AMB;5;5401 Ambien "
    "zolpidem tartrate zolpidem tartrate zolpidem hypromelloses lactose magnesium stearate"
)
GABAPENTIN = "GABAPENTIN gabapentin GABAPENTIN GABAPENTIN MANNITOL MAGNESIUM STEARATE"


@pytest.mark.parametrize(
    "text,name",
    [
        (TAGRISSO, "osimertinib"),
        (TAGRISSO, "Tagrisso"),
        (AMBIEN, "zolpidem tartrate"),
        (AMBIEN, "Ambien"),
        ("Aridol Bronchial Challenge Test Kit mannitol MANNITOL", "mannitol"),
        ("COUMADIN warfarin sodium ANHYDROUS LACTOSE WARFARIN SODIUM WARFARIN", "warfarin"),
    ],
)
def test_the_label_s_own_names_are_accepted(text, name):
    assert _names_product_itself(text, name)


@pytest.mark.parametrize(
    "text,name",
    [
        (TAGRISSO, "mannitol"),
        (AMBIEN, "magnesium stearate"),
        (AMBIEN, "polysorbate 80"),
        (AMBIEN, "titanium dioxide"),
        (GABAPENTIN, "magnesium stearate"),
        (GABAPENTIN, "gaba"),
    ],
)
def test_inactive_ingredients_and_partial_words_are_rejected(text, name):
    assert not _names_product_itself(text, name)


def _cfg(query_type):
    return {
        "name": f"FDA_{query_type}",
        "type": "FDALabelTool",
        "fields": {"query_type": query_type},
        "parameter": {"type": "object", "properties": {}},
    }


class _Resp:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def _unlinked(text, spl_id):
    return {"id": spl_id, "spl_product_data_elements": [text], "indications_and_usage": ["..."]}


def _run(query_type, arguments, corpus):
    issued = []

    def fake_get(url, params=None, timeout=None, headers=None, **kwargs):
        issued.append(params["search"])
        if params["search"] in corpus:
            return _Resp({"results": corpus[params["search"]]})
        return _Resp({"error": {"code": "NOT_FOUND"}}, status_code=404)

    with patch("tooluniverse.fda_label_tool.requests.get", side_effect=fake_get):
        return FDALabelTool(_cfg(query_type)).run(arguments), issued


def test_get_label_finds_an_unlinked_label_by_its_generic_name():
    corpus = {'spl_product_data_elements:"osimertinib"': [_unlinked(TAGRISSO, "tagrisso")]}
    out, issued = _run("get", {"drug_name": "osimertinib"}, corpus)

    assert out["status"] == "success"
    assert out["data"]["spl_id"] == "tagrisso"
    # With no openFDA names, the record says what the product is from its own text.
    assert out["data"]["product"].startswith("TAGRISSO osimertinib")
    # The linked-label searches still come first.
    assert issued[0] == 'openfda.generic_name:"osimertinib"'
    assert issued[-1] == 'spl_product_data_elements:"osimertinib"'


def test_an_inactive_ingredient_is_still_an_honest_miss():
    corpus = {
        'spl_product_data_elements:"magnesium stearate"': [
            _unlinked(GABAPENTIN, "gabapentin"),
            _unlinked(AMBIEN, "ambien"),
        ]
    }
    out, _ = _run("get", {"drug_name": "magnesium stearate"}, corpus)

    assert out["status"] == "error"
    assert "magnesium stearate" in out["error"]


def test_a_linked_match_is_returned_without_searching_product_text():
    linked = {"id": "erlotinib", "openfda": {"generic_name": ["ERLOTINIB HYDROCHLORIDE"]}}
    corpus = {'openfda.generic_name:"erlotinib"': [linked]}
    out, issued = _run("search", {"drug_name": "erlotinib", "limit": 3}, corpus)

    assert out["status"] == "success"
    assert [r["spl_id"] for r in out["data"]] == ["erlotinib"]
    assert "product" not in out["data"][0]
    assert not any(q.startswith("spl_product_data_elements") for q in issued)


def test_product_text_matches_on_labels_that_openfda_did_link_are_ignored():
    # A linked label reached only through product text matched on something other
    # than its own openFDA names, i.e. an ingredient. The name searches decide those.
    linked = {
        "id": "beizray",
        "openfda": {"generic_name": ["DOCETAXEL"]},
        "spl_product_data_elements": ["Albuminex albumin human ALBUMIN HUMAN ALBUMIN HUMAN"],
    }
    corpus = {'spl_product_data_elements:"albuminex"': [linked]}
    out, _ = _run("get", {"drug_name": "albuminex"}, corpus)

    assert out["status"] == "error"
