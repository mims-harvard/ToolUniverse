"""Unit tests for the annotate_variant_multi_source aggregator fixes.

Regression guard for Feature-KRAS-001: the parsers read the WRONG nested paths
(gnomAD data.gene.gene_id, CIViC data.gene.variants.nodes) so every source came
back empty, and sources_with_data falsely listed sources that returned nothing.
"""

from unittest.mock import patch

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


def test_summary_does_not_misattribute_unmatched_clinvar_context():
    """Fix-T2A-001: when clinvar has no exact match, `variants` holds unrelated
    gene-level fallback context (see test_parse_clinvar_falls_back_...). The
    summary must not report classifications[0] as if it were the queried
    variant's classification."""
    t = _tool()
    annotations = {
        "clinvar": {
            "total_gene_variants": 73,
            "matched": 0,
            "exact_match": False,
            "variants": [
                {"name": "NM_004333.6(BRAF):c.2209G>A (p.Gly737Ser)",
                 "classification": "Uncertain significance"},
            ],
        }
    }
    s = t._build_summary(annotations, variant="BRAF V600E")
    assert s["clinvar_classification"] is None
    assert "clinvar_note" in s


def test_summary_reports_classification_for_exact_clinvar_match():
    t = _tool()
    annotations = {
        "clinvar": {
            "total_gene_variants": 5,
            "matched": 1,
            "exact_match": True,
            "variants": [
                {"name": "NM_004333.6(BRAF):c.1799T>A (p.Val600Glu)",
                 "classification": "Pathogenic"},
            ],
        }
    }
    s = t._build_summary(annotations, variant="BRAF V600E")
    assert s["clinvar_classification"] == "Pathogenic"
    assert "clinvar_note" not in s


def test_sub_call_error_detects_error_status_dict():
    """Fix-R2B-003: sub-tools signal failure by returning
    {"status": "error", ...}, not by raising."""
    t = _tool()
    assert t._sub_call_error({"status": "error", "error": "boom"}) == "boom"
    assert t._sub_call_error({"status": "success", "data": {}}) is None
    assert t._sub_call_error(None) is None


def test_run_records_sub_call_failures_instead_of_empty_success():
    """Fix-R2B-003: when every underlying source call fails (returns an
    error dict, e.g. a network outage), the aggregator must report those
    failures in sources_failed rather than silently treating them as
    "gene has zero known variants" (a dangerous false negative for a
    clinically significant gene like BRCA1)."""
    t = _tool()

    def fake_run_one_function(call):
        return {"status": "error", "error": "Could not find a suitable TLS CA certificate bundle"}

    with patch(
        "tooluniverse.execute_function.ToolUniverse.run_one_function",
        side_effect=fake_run_one_function,
    ), patch(
        "tooluniverse.execute_function.ToolUniverse.load_tools", return_value=None
    ):
        result = t.run({"gene": "BRCA1", "rsid": "rs80357906"})

    data = result["data"]
    assert data["annotations"] == {}
    assert len(data["sources_failed"]) == 4
    assert all("TLS" in msg for msg in data["sources_failed"])
    assert data["sources_queried"] == []


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


def test_clinvar_classification_not_derived_from_unmatched_fallback():
    # Fix-R27A-1/T2A-001: confirmed live for EGFR L858R -- _parse_clinvar's
    # fallback context list (returned when exact_match is False) was
    # being blindly summarized as clinvar_classification, e.g. reporting
    # "Uncertain significance" (an unrelated p.Leu828Ser record) for a
    # variant that is actually ClinVar Oncogenic/Tier I-Strong. When
    # exact_match is False, clinvar_classification must be explicitly None
    # (not derived from the unrelated fallback record) and a clinvar_note
    # must explain why, rather than silently omitting the field.
    t = _tool()
    annotations = {
        "clinvar": {
            "total_gene_variants": 3167,
            "matched": 0,
            "exact_match": False,
            "variants": [
                {"name": "p.Leu828Ser", "classification": "Uncertain significance"},
            ],
        },
    }
    s = t._build_summary(annotations, variant="L858R", gene="EGFR")
    assert s["clinvar_classification"] is None
    assert "clinvar_note" in s


def test_clinvar_classification_set_when_exact_match_true():
    t = _tool()
    annotations = {
        "clinvar": {
            "total_gene_variants": 3167,
            "matched": 1,
            "exact_match": True,
            "variants": [
                {"name": "p.Leu858Arg", "classification": "Pathogenic"},
            ],
        },
    }
    s = t._build_summary(annotations, variant="L858R", gene="EGFR")
    assert s["clinvar_classification"] == "Pathogenic"
