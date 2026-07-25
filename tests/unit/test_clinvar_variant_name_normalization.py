"""Unit test: ClinVar_search_variants normalizes HGVS-prefixed / rsID variant_name.

Two false-empties (each flagged by multiple role-play personas):
- NCBI's [Variant name] index mangles the '.' in an unquoted HGVS reference
  prefix ('p.Glu342Lys' -> 'p0x2eGlu342Lys') and matches nothing, so a clinician
  typing standard HGVS got total_count 0 (SERPINA1 Z-allele exists as
  'Glu342Lys').
- An rsID passed as variant_name (rs776746 / rs35705950) was sent to the
  [Variant name] field, which returns 0, instead of a bare free-text search.

Fix-R3-07: stripping the prefix fixed protein notation but silently BROKE
coding notation, whose '+'/'>' characters Entrez only takes literally inside
quotes. Confirmed live that no single spelling works for both:

    DPYD     "c.1905+1G>A"[Variant name] -> 1   "1905+1G>A" -> 0
    SERPINA1 "p.Glu342Lys"[Variant name] -> 0   "Glu342Lys" -> 2

so an HGVS-prefixed name now contributes BOTH quoted spellings, OR'd together.
An OR can only add matches the old query missed, never drop ones it found.
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


def test_hgvs_protein_prefix_stripped_spelling_is_offered():
    term = _term_for({"gene": "SERPINA1", "variant_name": "p.Glu342Lys"})
    # The stripped spelling is the one that actually matches for protein HGVS.
    assert '"Glu342Lys"[Variant name]' in term
    # ...and the prefix-intact spelling rides along for the coding case.
    assert '"p.Glu342Lys"[Variant name]' in term
    assert " OR " in term
    # The mangled form must never be constructed by us.
    assert "p0x2e" not in term


@pytest.mark.parametrize("prefix", ["p.", "c.", "g.", "m.", "n.", "P.", "C."])
def test_all_reference_prefixes_offer_the_stripped_spelling(prefix):
    term = _term_for({"variant_name": f"{prefix}Glu342Lys"})
    assert '"Glu342Lys"[Variant name]' in term
    assert f'"{prefix}Glu342Lys"[Variant name]' in term


def test_coding_hgvs_keeps_its_prefix_quoted():
    """Fix-R3-07: 'c.1905+1G>A' matches ONLY with the prefix kept and quoted."""
    term = _term_for({"gene": "DPYD", "variant_name": "c.1905+1G>A"})
    assert '"c.1905+1G>A"[Variant name]' in term


def test_rsid_as_variant_name_becomes_bare_term():
    term = _term_for({"gene": "CYP3A5", "variant_name": "rs776746"})
    assert "rs776746" in term
    assert "rs776746[Variant name]" not in term  # NOT wrapped in the field tag
    assert '"rs776746"[Variant name]' not in term


def test_plain_protein_change_unchanged():
    term = _term_for({"gene": "SERPINA1", "variant_name": "Glu342Lys"})
    assert '"Glu342Lys"[Variant name]' in term
    # No prefix to strip, so there is nothing to OR against.
    assert " OR " not in term


def test_short_protein_change_not_mangled():
    # 'V600E' has no reference prefix; must pass through untouched.
    term = _term_for({"gene": "BRAF", "variant_name": "V600E"})
    assert '"V600E"[Variant name]' in term
    assert " OR " not in term
