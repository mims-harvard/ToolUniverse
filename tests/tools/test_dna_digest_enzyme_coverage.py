"""Regression test: DNA_virtual_digest resolves uncommon enzymes via Biopython
fallback (not just the ~25 hardcoded NEB enzymes) while keeping NEB behavior."""
import os
from tooluniverse.dna_tools import DNATool, _resolve_enzyme, _site_to_regex

def _tool():
    cfg = {"name": "DNA_virtual_digest", "parameter": {}}
    return DNATool(cfg)

def _nfrag(seq, enzymes):
    r = _tool().run({"operation": "virtual_digest", "sequence": seq, "enzymes": enzymes})
    assert r["status"] == "success", r
    return r["data"].get("n_fragments", r["data"].get("num_fragments"))

def test_site_to_regex_iupac():
    assert _site_to_regex("GAATTC") == "GAATTC"
    assert _site_to_regex("AGCT") == "AGCT"
    assert _site_to_regex("GANTC") == "GA[ACGT]TC"

def test_resolve_neb_and_biopython():
    assert _resolve_enzyme("EcoRI")[1] == "GAATTC"           # built-in
    r = _resolve_enzyme("AluBI")                              # biopython fallback
    assert r is not None and r[1]                             # has a recognition site
    assert _resolve_enzyme("NotARealEnzymeXYZ") is None

def test_common_enzymes_unchanged():
    assert _nfrag("AAAGAATTCAAAGGATCCAAA", ["EcoRI", "BamHI"]) == 3

def test_uncommon_enzymes_resolved():
    # AluBI (AG^CT) is an AluI isoschizomer absent from the hardcoded NEB table.
    n = _nfrag("AAAGAATTCAGCTAAAGCTAA", ["AluBI"])
    assert isinstance(n, int) and n >= 2   # at least cuts the AGCT sites

def test_all_unknown_errors():
    r = _tool().run({"operation": "virtual_digest", "sequence": "ACGTACGT",
                     "enzymes": ["FooI", "BarII"]})
    assert r["status"] == "error"
