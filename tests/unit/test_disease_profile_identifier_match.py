"""gather_disease_profile must not mix several diseases into one identifier set.

Every source behind the profile is a ranked search, and their top hits
disagree. For "mucopolysaccharidosis type I" the profile used to emit Orphanet
583 (MPS VI), MeSH D009085 (MPS IV) and ORDO 217085 (MPS II severe form)
together under one disease name, because the first hit of each source was
accepted without checking its label.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.compound_disease_tool import (
    CompoundDiseaseProfileTool,
    _labels_match,
)

pytestmark = pytest.mark.unit


def _tool():
    return CompoundDiseaseProfileTool(
        {"name": "gather_disease_profile", "type": "CompoundDiseaseProfileTool"}
    )


def test_roman_and_arabic_subtype_numbers_are_the_same_disease():
    assert _labels_match("mucopolysaccharidosis type I", "Mucopolysaccharidosis type 1")
    assert _labels_match("mucopolysaccharidosis type I", "Mucopolysaccharidosis Type I")


def test_different_subtype_numbers_are_different_diseases():
    assert not _labels_match(
        "mucopolysaccharidosis type I", "Mucopolysaccharidosis type 6"
    )
    assert not _labels_match("mucopolysaccharidosis type I", "Mucopolysaccharidosis IV")


def test_orphanet_hit_is_chosen_by_name_not_by_rank():
    result = {
        "status": "success",
        "data": {
            "results": [
                {"ORPHAcode": 583, "Preferred term": "Mucopolysaccharidosis type 6"},
                {"ORPHAcode": 579, "Preferred term": "Mucopolysaccharidosis type 1"},
            ]
        },
    }

    parsed = _tool()._parse_orphanet(result, "mucopolysaccharidosis type I")

    assert parsed["orpha_code"] == "579"
    assert parsed["match"] == "exact"


def test_orphanet_without_a_name_match_is_flagged_and_not_promoted():
    result = {
        "status": "success",
        "data": {
            "results": [
                {"ORPHAcode": 583, "Preferred term": "Mucopolysaccharidosis type 6"}
            ]
        },
    }
    tool = _tool()

    parsed = tool._parse_orphanet(result, "mucopolysaccharidosis type I")
    assert parsed["match"] == "approximate"

    profile = tool._build_profile(
        "mucopolysaccharidosis type I",
        {"orphanet": parsed, "ols": {}, "opentargets": {}},
    )
    assert "orphanet" not in profile["identifiers"]


def test_only_label_matching_ontology_terms_become_identifiers():
    sections = {
        "orphanet": {},
        "opentargets": {},
        "ols": {
            "terms": [
                {
                    "id": "NCIT:C85053",
                    "label": "Mucopolysaccharidosis Type I",
                    "ontology": "ncit",
                },
                {
                    "id": "mesh:D009085",
                    "label": "Mucopolysaccharidosis IV",
                    "ontology": "mesh",
                },
                {
                    "id": "ORDO:217085",
                    "label": "Mucopolysaccharidosis type 2, severe form",
                    "ontology": "ordo",
                },
            ]
        },
    }

    profile = _tool()._build_profile("mucopolysaccharidosis type I", sections)

    assert profile["identifiers"] == {"ncit": "NCIT:C85053"}
