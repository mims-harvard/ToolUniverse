"""Type IIS enzymes (BsaI, BbsI, Esp3I/BsmBI, SapI) cut OUTSIDE their recognition
site -- that offset is the whole basis of Golden Gate / MoClo assembly.

Two defects made them unusable:

1. `_resolve_enzyme` read `enz.fst` from Biopython, but the attribute is `fst5`.
   The lookup always raised, so EVERY enzyme resolved through the Biopython
   fallback silently got a midpoint cut. Esp3I cut inside CGT^CTC instead of 7 nt
   downstream, so digest fragments and Golden Gate overhangs were wrong.
2. `find_restriction_sites` validated only against the 25-enzyme NEB table and
   never used the fallback, so it rejected BsaI outright while `virtual_digest`
   accepted it.

`fst5` reproduces all 25 curated NEB_CUT_OFFSETS exactly, so it is the correct
source for both curated and fallback enzymes.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.dna_tools import (
    NEB_CUT_OFFSETS,
    DNATool,
    _resolve_enzyme,
)

pytestmark = pytest.mark.unit

DIGEST = {"name": "DNA_virtual_digest", "type": "DNATool",
          "fields": {"operation": "virtual_digest"}}
SITES = {"name": "DNA_find_restriction_sites", "type": "DNATool",
         "fields": {"operation": "find_restriction_sites"}}

# CGTCTC (Esp3I) at index 4 and 27; Type IIS cut is site_start + 7.
TYPE_IIS_SEQ = "AAAACGTCTCATTTTGGGGCCCCAAAACGTCTCAGGGGTTTTAAAACCCC"


@pytest.mark.parametrize(
    "enzyme,site,offset",
    [
        ("Esp3I", "CGTCTC", 7),
        ("BsmBI", "CGTCTC", 7),
        ("BsaI", "GGTCTC", 7),
        ("BbsI", "GAAGAC", 8),
        ("SapI", "GCTCTTC", 8),
    ],
)
def test_type_iis_offsets_are_outside_the_site(enzyme, site, offset):
    resolved = _resolve_enzyme(enzyme)
    assert resolved is not None, f"{enzyme} did not resolve"
    _name, resolved_site, resolved_off = resolved
    assert resolved_site == site
    assert resolved_off == offset, f"{enzyme} must cut {offset} nt from site start"
    assert resolved_off >= len(site), "Type IIS must cut outside its recognition site"


def test_curated_offsets_unchanged_by_the_fallback():
    """The 25 hand-curated enzymes must keep their exact offsets."""
    for name, expected in NEB_CUT_OFFSETS.items():
        _n, _s, off = _resolve_enzyme(name)
        assert off == expected, f"{name}: {off} != curated {expected}"


def test_virtual_digest_cuts_downstream_for_type_iis():
    result = DNATool(DIGEST).run(
        {"sequence": TYPE_IIS_SEQ, "enzymes": ["Esp3I"], "circular": False}
    )
    assert result["status"] == "success", result.get("error")
    positions = sorted(c["position"] for c in result["data"]["cut_sites"])
    assert positions == [11, 34], f"expected Type IIS cuts at 11/34, got {positions}"


def test_find_restriction_sites_accepts_type_iis():
    """BsaI was rejected here while the digest tool resolved it."""
    result = DNATool(SITES).run(
        {"sequence": "AAAAGGTCTCATTTTGGGGGGTCTCAAAA", "enzymes": ["BsaI"]}
    )
    assert result["status"] == "success", result.get("error")
    assert "BsaI" in result["data"]["enzymes_with_sites"]


def test_unknown_enzyme_still_errors():
    result = DNATool(SITES).run(
        {"sequence": "AAAAGGTCTCAAAA", "enzymes": ["NotARealEnzyme9"]}
    )
    assert result["status"] == "error"
    assert "NotARealEnzyme9" in result["error"]


# ---------------------------------------------------------------------------
# Both-strand search. Recognition sites are palindromic only for a minority of
# enzymes; a non-palindromic site also occurs reverse-complemented. The scan was
# forward-strand-only, so it found half the sites -- and a Golden Gate plasmid
# carries its two Type IIS sites INVERTED around the insert, so each real plasmid
# reported 1 site and came back "uncut" (1 fragment). Verified on the three
# LAB-Bench CloningScenarios plasmids: each has one CGTCTC and one GAGACG.
# ---------------------------------------------------------------------------

# One forward site (CGTCTC @16) and one reverse site (GAGACG @46).
INVERTED_SEQ = (
    "AAAACCCCTTTTGGGG" "CGTCTC" "ATTTTCCCCGGGGAAAATTTTCCCC" "GAGACG" "TTTTAAAACCCC"
)


def test_finds_reverse_strand_sites():
    result = DNATool(SITES).run({"sequence": INVERTED_SEQ, "enzymes": ["Esp3I"]})
    assert result["status"] == "success", result.get("error")
    sites = result["data"]["enzymes_with_sites"]["Esp3I"]["cut_sites"]
    assert len(sites) == 2, f"expected both orientations, got {sites}"


def test_digest_cuts_inverted_type_iis_pair():
    result = DNATool(DIGEST).run(
        {"sequence": INVERTED_SEQ, "enzymes": ["Esp3I"], "circular": False}
    )
    assert result["status"] == "success", result.get("error")
    assert len(result["data"]["fragments"]) == 3, "two cuts must give three fragments"


def test_palindromic_site_is_not_double_counted():
    """EcoRI's site equals its own reverse complement -- one site, one cut."""
    seq = "AAAA" + "GAATTC" + "AAAACCCCGGGG"
    sites = DNATool(SITES).run({"sequence": seq, "enzymes": ["EcoRI"]})
    assert sites["data"]["enzymes_with_sites"]["EcoRI"]["cut_sites"] == [5]
    digest = DNATool(DIGEST).run(
        {"sequence": seq, "enzymes": ["EcoRI"], "circular": False}
    )
    assert len(digest["data"]["fragments"]) == 2, "one cut must give two fragments"


def test_circular_plasmid_with_inverted_pair_yields_two_fragments():
    result = DNATool(DIGEST).run(
        {"sequence": INVERTED_SEQ, "enzymes": ["Esp3I"], "circular": True}
    )
    assert result["status"] == "success", result.get("error")
    assert len(result["data"]["fragments"]) == 2, "circular + 2 cuts -> 2 fragments"
