"""An identifier search must not be used to trim the label text it returns.

Fetching a label by ``id`` and asking for its sections returned nothing: the
searched value was appended to the keyword filter, and no sentence in a label
contains its own UUID, so every requested section was trimmed away.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tooluniverse.openfda_tool import (  # noqa: E402
    contributes_content_keywords,
    extract_nested_fields,
)

LABEL = {
    "id": "e9f12b84-2885-442d-b53c-0fd5a9946d38",
    "set_id": "9b1f2d4c-0000-4d10-9a2b-1a2b3c4d5e6f",
    "effective_time": "20240101",
    "indications_and_usage": [
        "INDICATIONS AND USAGE Ceftriaxone for Injection is indicated for lower "
        "respiratory tract infections."
    ],
    "contraindications": [
        "CONTRAINDICATIONS Ceftriaxone is contraindicated in patients with known "
        "hypersensitivity to cephalosporins."
    ],
}
SECTIONS = ["id", "indications_and_usage", "contraindications"]


def test_identifier_and_name_fields_never_become_content_keywords():
    for field in ("id", "set_id", "spl_id", "effective_time", "version",
                  "openfda.generic_name", "openfda.brand_name", "openfda.unii"):
        assert not contributes_content_keywords(field), field


def test_real_content_fields_still_become_content_keywords():
    for field in ("indications_and_usage", "contraindications", "openfda.route"):
        assert contributes_content_keywords(field), field


def test_a_tuple_of_name_fields_contributes_nothing():
    assert not contributes_content_keywords(("openfda.generic_name", "openfda.brand_name"))


def test_searching_by_id_would_have_emptied_every_section():
    """The old behaviour, reproduced directly on the extractor."""
    trimmed = extract_nested_fields([LABEL], SECTIONS, [LABEL["id"]])
    assert trimmed == [] or all(
        not record.get(section) for record in trimmed
        for section in ("indications_and_usage", "contraindications")
    )


def test_without_the_identifier_keyword_the_sections_survive():
    kept = extract_nested_fields([LABEL], SECTIONS, [])
    assert len(kept) == 1
    assert "lower respiratory tract infections" in str(kept[0]["indications_and_usage"])
    assert "hypersensitivity to cephalosporins" in str(kept[0]["contraindications"])
    assert kept[0]["id"] == LABEL["id"]
