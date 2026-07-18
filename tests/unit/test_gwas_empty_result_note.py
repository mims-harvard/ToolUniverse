"""Regression guard for Fix-R11B-2: GWASRESTTool._empty_result_note
previously suggested retrying with a different disease_trait text query,
using a hardcoded, unrelated example ("colorectal cancer") that didn't
adapt to the caller's actual query. Confirmed live that for a real
empty-result case (LCT/lactase persistence), the trait itself was
resolvable but simply had no directly-tagged associations -- the
associations existed under other EFO terms, and the tool that actually
found them was GWAS_search_associations_by_gene/gwas_get_snps_for_gene
(gene-based lookup), not a reworded trait string. The note now points to
that real fallback.
"""

import pytest

from tooluniverse.gwas_tool import GWASRESTTool

pytestmark = pytest.mark.unit


def test_note_no_longer_uses_generic_hardcoded_example():
    note = GWASRESTTool._empty_result_note("MONDO_0100345")
    assert "colorectal cancer" not in note


def test_note_points_to_gene_based_search_fallback():
    note = GWASRESTTool._empty_result_note("MONDO_0100345")
    assert "GWAS_search_associations_by_gene" in note
    assert "gwas_get_snps_for_gene" in note


def test_note_includes_the_efo_id():
    note = GWASRESTTool._empty_result_note("MONDO_0100345")
    assert "MONDO_0100345" in note
