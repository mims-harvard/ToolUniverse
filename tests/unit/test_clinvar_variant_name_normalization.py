"""Unit test: ClinVar_search_variants normalizes HGVS-prefixed / rsID variant_name.

Two false-empties (each flagged by multiple role-play personas):
- NCBI's [Variant name] index mangles the '.' in an HGVS reference prefix
  ('p.Glu342Lys' -> 'p0x2eGlu342Lys') and matches nothing, so a clinician typing
  standard HGVS got total_count 0 (SERPINA1 Z-allele exists as 'Glu342Lys').
- An rsID passed as variant_name (rs776746 / rs35705950) was sent to the
  [Variant name] field, which returns 0, instead of a bare free-text search.
"""
from unittest.mock import patch

import pytest

from tooluniverse.clinvar_tool import ClinVarSearchVariants

pytestmark = pytest.mark.unit


def _term_for(arguments):
    tool = ClinVarSearchVariants({"name": "ClinVar_search_variants"})
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        return_value={"status": "success", "data": {}},
    ) as mock_request:
        tool.run(arguments)
    return mock_request.call_args[0][1]["term"]


def test_hgvs_protein_prefix_stripped():
    term = _term_for({"gene": "SERPINA1", "variant_name": "p.Glu342Lys"})
    assert "Glu342Lys[Variant name]" in term
    assert "p.Glu342Lys" not in term
    assert "p0x2e" not in term


@pytest.mark.parametrize("prefix", ["p.", "c.", "g.", "m.", "n.", "P.", "C."])
def test_all_reference_prefixes_stripped(prefix):
    term = _term_for({"variant_name": f"{prefix}Glu342Lys"})
    assert "Glu342Lys[Variant name]" in term
    assert prefix not in term


def test_rsid_as_variant_name_becomes_bare_term():
    term = _term_for({"gene": "CYP3A5", "variant_name": "rs776746"})
    assert "rs776746" in term
    assert "rs776746[Variant name]" not in term  # NOT wrapped in the field tag


def test_plain_protein_change_unchanged():
    term = _term_for({"gene": "SERPINA1", "variant_name": "Glu342Lys"})
    assert "Glu342Lys[Variant name]" in term


def test_short_protein_change_not_mangled():
    # 'V600E' has no reference prefix; must pass through untouched.
    term = _term_for({"gene": "BRAF", "variant_name": "V600E"})
    assert "V600E[Variant name]" in term
