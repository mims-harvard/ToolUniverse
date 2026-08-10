"""Regression guard for the mydisease.info-backed CTD tool's term routing.

mydisease.info indexes CTD's chemical-disease curation under distinct nested
fields per identifier type (mesh_chemical_id, cas_registry_number,
chemical_name) with no fuzzy cross-matching between them, so a chemical term
must be routed to the right field before querying. `_chemical_match_field`
picks that field from a bare term's shape (MeSH ID pattern, CAS RN pattern,
or an explicit 'PREFIX:value' CURIE); `_term_and_prefix` does the CURIE
splitting it relies on.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.ctd_tool import _chemical_match_field, _term_and_prefix

pytestmark = pytest.mark.unit


def test_bare_mesh_supplementary_concept_id_matches_mesh_field():
    assert _chemical_match_field("C006780") == ("mesh_chemical_id", "C006780")


def test_bare_mesh_descriptor_id_matches_mesh_field():
    assert _chemical_match_field("D016729") == ("mesh_chemical_id", "D016729")


def test_bare_cas_rn_matches_cas_field():
    assert _chemical_match_field("80-05-7") == ("cas_registry_number", "80-05-7")


def test_plain_name_matches_chemical_name_field():
    assert _chemical_match_field("bisphenol A") == ("chemical_name", "bisphenol A")
    assert _chemical_match_field("paracetamol") == ("chemical_name", "paracetamol")


def test_explicit_mesh_curie_matches_mesh_field_by_value():
    assert _chemical_match_field("MESH:C006780") == ("mesh_chemical_id", "C006780")


def test_explicit_cas_curie_matches_cas_field_by_value():
    assert _chemical_match_field("CAS:80-05-7") == ("cas_registry_number", "80-05-7")


def test_unrecognized_curie_prefix_falls_back_to_name_field():
    # CHEBI/PubChem/etc. CURIEs aren't stored in mydisease.info's CTD cache,
    # so they can't be routed to a specific field -- the whole term
    # (including prefix) is matched as a literal name, which will correctly
    # find nothing rather than silently guessing a field.
    assert _chemical_match_field("CHEBI:27563") == ("chemical_name", "CHEBI:27563")


def test_term_and_prefix_splits_on_first_colon():
    assert _term_and_prefix("MESH:C006780") == ("MESH", "C006780")
    assert _term_and_prefix("bisphenol A") == (None, "bisphenol A")
