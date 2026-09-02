"""Label identifiers must survive keyword trimming (Fix-R44).

``extract_nested_fields`` trims a long label section down to the sentences
mentioning the caller's search terms. It skipped that trimming for exactly three
hard-coded keys (``openfda``, ``generic_name``, ``brand_name``) and trimmed
everything else -- including document IDENTIFIERS, which contain no sentences at
all. Trimming a UUID therefore produced ``""``, and the empty string was
published as if it were the field's value.

Measured live 2026-08-12::

    $ python -m tooluniverse.cli run FDA_get_drug_label_info_by_field_value \\
        '{"field":"precautions","field_value":"Loa loa","limit":1,
          "return_fields":["id","set_id","openfda.generic_name"]}'
    "id": ""
    "set_id": ""
    "openfda.generic_name": ["IVERMECTIN"]

while openFDA carries ``id: 06f2293c-2cf4-70d4-e063-6394a90a3a56`` and
``set_id: 014e33e7-c07d-4feb-a2cf-7cd160b1facd`` on that record. The loss was
total rather than partial: round-tripping a known ``set_id`` back through the
tool matched exactly the right label and still returned ``""``.

Why it matters: the SPL set id is the only stable handle for a label VERSION, so
a reader could not cite or re-fetch the exact ivermectin revision carrying the
Loa loa encephalopathy precaution -- and the tool's own description recommends
both fields.
"""

import pytest

pytestmark = pytest.mark.unit

SET_ID = "014e33e7-c07d-4feb-a2cf-7cd160b1facd"
DOC_ID = "06f2293c-2cf4-70d4-e063-6394a90a3a56"

RECORD = {
    "id": DOC_ID,
    "set_id": SET_ID,
    "effective_time": "20240101",
    # openFDA returns label sections as arrays of strings, not bare strings.
    "precautions": [
        "Rarely, patients with onchocerciasis who are also heavily infected "
        "with Loa loa may develop a serious or even fatal encephalopathy. "
        "An unrelated sentence about storage conditions."
    ],
    "openfda": {"generic_name": ["IVERMECTIN"]},
}


def _extract(fields, keywords):
    from tooluniverse.openfda_tool import extract_nested_fields

    return extract_nested_fields([RECORD], fields, keywords=keywords)[0]


def test_identifiers_survive_a_keyword_filter():
    row = _extract(["id", "set_id", "effective_time", "precautions"], ["Loa loa"])

    assert row["id"] == DOC_ID
    assert row["set_id"] == SET_ID
    assert row["effective_time"] == "20240101"


def test_prose_sections_are_still_trimmed():
    """The fix must not disable trimming -- that is the feature, not the defect."""
    row = _extract(["precautions"], ["Loa loa"])

    assert "Loa loa" in row["precautions"]
    assert "storage conditions" not in row["precautions"]


def test_name_blocks_still_bypass_trimming():
    row = _extract(["openfda.generic_name"], ["Loa loa"])

    assert row["openfda.generic_name"] == ["IVERMECTIN"]


def test_the_rule_is_a_named_set_not_a_chain_of_comparisons():
    """Pins the generalisation, so a new identifier is added in one place.

    The previous form was `key != "openfda" and key != "generic_name" and
    key != "brand_name"`, which is why `id` and `set_id` were never considered.
    """
    from tooluniverse.openfda_tool import NEVER_KEYWORD_TRIMMED

    assert {"id", "set_id", "openfda", "generic_name", "brand_name"} <= (
        NEVER_KEYWORD_TRIMMED
    )
