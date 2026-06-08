"""Unit tests for the annotate_variant_multi_source aggregator fixes.

Regression guard for Feature-KRAS-001: the parsers read the WRONG nested paths
(gnomAD data.gene.gene_id, CIViC data.gene.variants.nodes) so every source came
back empty, and sources_with_data falsely listed sources that returned nothing.
"""

from tooluniverse.compound_variant_tool import (
    CompoundVariantAnnotationTool,
    _variant_match_forms,
    _title_matches,
)


def _tool():
    return CompoundVariantAnnotationTool(
        {"name": "annotate_variant_multi_source", "type": "CompoundVariantAnnotationTool",
         "parameter": {"type": "object", "properties": {}}}
    )


def test_variant_match_forms_expands_to_hgvs_3letter():
    forms = _variant_match_forms("V600E")
    assert "v600e" in forms
    assert "val600glu" in forms  # ClinVar HGVS form
    assert _title_matches("NM_004333.6(BRAF):c.1799T>A (p.Val600Glu)", "V600E")
    assert _title_matches("BRAF V600E", "V600E")
    assert not _title_matches("p.Gly12Cys", "V600E")


def test_parse_gnomad_reads_nested_gene():
    t = _tool()
    real = {"status": "success", "data": {"gene": {
        "gene_id": "ENSG00000157764", "symbol": "BRAF", "name": "B-Raf", "chrom": "7",
        "canonical_transcript_id": "ENST00000646891"}}}
    out = t._parse_gnomad(real)
    assert out["gene_id"] == "ENSG00000157764"
    assert out["symbol"] == "BRAF"
    # missing gene → empty (not a misleading partial)
    assert t._parse_gnomad({"status": "success", "data": {}}) == {}


def test_parse_civic_reads_nested_nodes_and_filters():
    t = _tool()
    real = {"data": {"gene": {"id": 5, "name": "BRAF", "variants": {"nodes": [
        {"id": 12, "name": "V600E", "feature": {"name": "BRAF"}},
        {"id": 99, "name": "V600K"}]}}}}
    out = t._parse_civic(real, "V600E")
    assert out["total_gene_variants"] == 2
    assert out["matched"] == 1
    assert out["variants"][0]["name"] == "V600E"
    assert out["variants"][0]["civic_id"] == 12


def test_parse_clinvar_falls_back_to_gene_context_when_no_exact_match():
    t = _tool()
    real = {"data": {"total_count": 66, "variants": [
        {"title": "NM_004333.6(BRAF):c.96C>G (p.Gly32=)", "clinical_significance": "Likely benign"},
        {"title": "NM_004333.6(BRAF):c.1018A>G (p.Ile340Val)", "clinical_significance": "Benign"}]}}
    out = t._parse_clinvar(real, "V600E")
    assert out["total_gene_variants"] == 66
    assert out["matched"] == 0
    assert out["exact_match"] is False
    assert len(out["variants"]) == 2  # gene-level context, not empty


def test_sources_with_data_is_honest():
    t = _tool()
    # gnomAD has a gene, CIViC matched one, ClinVar empty, UniProt empty
    annotations = {
        "clinvar": {"total_gene_variants": 0, "matched": 0, "variants": []},
        "gnomad": {"gene_id": "ENSG00000157764", "symbol": "BRAF"},
        "civic": {"matched": 1, "variants": [{"name": "V600E"}]},
        "uniprot": {"raw": "..."},
    }
    s = t._build_summary(annotations, variant="V600E", gene="BRAF")
    assert set(s["sources_with_data"]) == {"gnomad", "civic"}  # NOT clinvar/uniprot
    assert s["gnomad_gene_id"] == "ENSG00000157764"
    assert s["civic_variants_matched"] == 1
