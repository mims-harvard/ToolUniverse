"""Regression guard for Fix-R18C-2/4: CTD's own tool descriptions promise
bare CAS RN, bare MeSH ID, and bare NCBI Gene ID as valid input_terms
formats, but the RENCI Automat mirror's equivalent_identifiers only ever
store the CURIE-prefixed form -- confirmed live that "D000082" (bare MeSH
descriptor ID), "C006780" (bare MeSH supplementary-concept ID), "80-05-7"
(bare CAS RN), and "7157" (bare NCBI Gene ID) all failed to resolve while
their "MESH:"/"CAS:"/"NCBIGene:"-prefixed forms succeeded.
_candidate_curies() now tries the correctly-prefixed form first for
recognizable ID patterns, always falling back to the original string so a
name or already-prefixed CURIE keeps working unchanged.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.ctd_tool import _candidate_curies

pytestmark = pytest.mark.unit


def test_bare_mesh_descriptor_id_gets_prefixed_for_chem():
    assert _candidate_curies("D000082", "chem") == ["MESH:D000082", "D000082"]


def test_bare_mesh_supplementary_concept_id_gets_prefixed_for_chem():
    assert _candidate_curies("C006780", "chem") == ["MESH:C006780", "C006780"]


def test_bare_cas_rn_gets_prefixed_for_chem():
    assert _candidate_curies("80-05-7", "chem") == ["CAS:80-05-7", "80-05-7"]


def test_bare_ncbi_gene_id_gets_prefixed_for_gene():
    assert _candidate_curies("7157", "gene") == ["NCBIGene:7157", "7157"]


def test_bare_mesh_id_gets_prefixed_for_disease():
    assert _candidate_curies("D001943", "disease") == ["MESH:D001943", "D001943"]


def test_already_prefixed_curie_is_passed_through_unchanged():
    assert _candidate_curies("MESH:D000082", "chem") == ["MESH:D000082"]
    assert _candidate_curies("CAS:80-05-7", "chem") == ["CAS:80-05-7"]


def test_plain_name_has_no_id_candidates_generated():
    assert _candidate_curies("bisphenol A", "chem") == ["bisphenol A"]
    assert _candidate_curies("paracetamol", "chem") == ["paracetamol"]


def test_gene_symbol_is_not_treated_as_a_gene_id():
    assert _candidate_curies("TP53", "gene") == ["TP53"]


def test_all_digit_string_is_not_treated_as_gene_id_for_chem_type():
    # A bare numeric string only means "NCBI Gene ID" when input_type is
    # "gene" -- for chemical tools it's not auto-prefixed as anything.
    assert _candidate_curies("7157", "chem") == ["7157"]
