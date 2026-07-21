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
    assert out["exact_match"] is True
    assert out["variants"][0]["name"] == "V600E"
    assert out["variants"][0]["civic_id"] == 12


def test_parse_civic_gene_only_query_reports_zero_matched_not_all():
    """Fix-R51A-1: a gene-only query (variant_token=None) previously counted
    EVERY gene-level CIViC variant as "matched" -- the filter's
    "if variant_token and not _title_matches(...): continue" never actually
    skipped anything when variant_token was falsy, so matched silently
    equaled total_gene_variants, wrongly implying real matches against a
    filter that was never applied. Confirmed live for MSH2 (gene-only):
    matched=8 out of 8 total before the fix. ClinVar's parser already gets
    this right (matched=0, gene-level rows shown as unmatched context) --
    CIViC's must mirror that same shape."""
    t = _tool()
    real = {"data": {"gene": {"id": 5, "name": "MSH2", "variants": {"nodes": [
        {"id": 1, "name": "A1"}, {"id": 2, "name": "A2"}, {"id": 3, "name": "A3"}]}}}}

    out = t._parse_civic(real, None)

    assert out["total_gene_variants"] == 3
    assert out["matched"] == 0
    assert out["exact_match"] is False
    # Still surfaces gene-level context, just not mislabeled as a match.
    assert len(out["variants"]) == 3


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


def test_parse_clinvar_rows_have_no_condition_key():
    """Fix-R31A-3: ClinVar_search_variants rows never carry a "condition"
    field (confirmed live) -- condition is a search filter on that tool,
    not something it returns. The old code silently emitted "condition": ""
    for every row."""
    t = _tool()
    real = {"data": {"total_count": 1, "variants": [
        {"title": "NM_004004.6(GJB2):c.283G>C (p.Val95Leu)", "clinical_significance": "VUS"}]}}
    out = t._parse_clinvar(real)
    assert "condition" not in out["variants"][0]


def test_parse_uniprot_reads_results_list_not_bare_list():
    """Fix-R31A-4: UniProt_search's "data" is a dict with a "results" list
    ({"total_results": N, "results": [...]}), not itself a list -- confirmed
    live this always fell through to the raw-repr-string escape hatch,
    truncating mid-object. Field is "gene_names" (a list), not "gene_name"."""
    t = _tool()
    real = {
        "status": "success",
        "data": {
            "total_results": 1,
            "returned": 1,
            "results": [
                {
                    "accession": "P05091",
                    "protein_name": "Aldehyde dehydrogenase, mitochondrial",
                    "gene_names": ["ALDH2"],
                    "function": "Mitochondrial aldehyde dehydrogenase",
                }
            ],
        },
    }
    out = t._parse_uniprot(real)
    assert out["accession"] == "P05091"
    assert out["gene_name"] == "ALDH2"
    assert "raw" not in out


def test_parse_uniprot_falls_back_to_raw_for_unexpected_shape():
    t = _tool()
    out = t._parse_uniprot({"status": "success", "data": {"unexpected": "shape"}})
    assert "raw" in out


def test_parse_uniprot_prefers_exact_gene_match_over_top_relevance_hit():
    """Fix-R62A-2: blindly taking results[0] silently returned the WRONG
    gene's protein for gene-symbol families sharing a name prefix --
    confirmed live querying "GBA" (glucocerebrosidase/Gaucher disease,
    renamed to "GBA1" in 2023): UniProt's own relevance ranking put "GBA3"
    (cytosolic beta-glucosidase, a completely different, unrelated enzyme)
    at position 0, with a real GBA entry only at position 3 (still tagged
    with the legacy "GBA" symbol in that record's own gene_names)."""
    t = _tool()
    real = {
        "status": "success",
        "data": {
            "results": [
                {
                    "accession": "Q9H227",
                    "protein_name": "Cytosolic beta-glucosidase",
                    "gene_names": ["GBA3"],
                },
                {
                    "accession": "Q9HCG7",
                    "protein_name": "Non-lysosomal glucosylceramidase",
                    "gene_names": ["GBA2"],
                },
                {
                    "accession": "P04062",
                    "protein_name": "Lysosomal acid glucosylceramidase",
                    "gene_names": ["GBA1"],
                },
                {
                    "accession": "A0A068F658",
                    "protein_name": "Glucosylceramidase",
                    "gene_names": ["GBA"],
                },
            ],
        },
    }
    out = t._parse_uniprot(real, gene="GBA")
    assert out["accession"] == "A0A068F658"
    assert out["gene_name"] == "GBA"


def test_parse_uniprot_matches_case_insensitively():
    t = _tool()
    real = {
        "status": "success",
        "data": {
            "results": [
                {"accession": "WRONG", "protein_name": "unrelated", "gene_names": ["OTHER"]},
                {"accession": "P51587", "protein_name": "BRCA2", "gene_names": ["BRCA2"]},
            ],
        },
    }
    out = t._parse_uniprot(real, gene="brca2")
    assert out["accession"] == "P51587"


def test_parse_uniprot_falls_back_to_top_hit_when_no_gene_matches():
    """When none of the fetched results' gene_names match the queried gene
    at all (the gene truly isn't among them, not just mis-ranked), the old
    top-hit behavior is the only reasonable fallback -- must not error or
    return nothing."""
    t = _tool()
    real = {
        "status": "success",
        "data": {
            "results": [
                {"accession": "P05091", "protein_name": "ALDH2", "gene_names": ["ALDH2"]},
            ],
        },
    }
    out = t._parse_uniprot(real, gene="COMPLETELY_UNRELATED_GENE")
    assert out["accession"] == "P05091"


def test_parse_uniprot_without_gene_arg_keeps_old_top_hit_behavior():
    """Backward compatibility: gene defaults to None, so callers that don't
    pass it (or genuinely have no gene) get exactly the pre-fix behavior."""
    t = _tool()
    real = {
        "status": "success",
        "data": {
            "results": [
                {"accession": "FIRST", "protein_name": "x", "gene_names": ["A"]},
                {"accession": "SECOND", "protein_name": "y", "gene_names": ["B"]},
            ],
        },
    }
    out = t._parse_uniprot(real)
    assert out["accession"] == "FIRST"


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


def test_clinvar_sub_call_uses_gene_param_not_query_alias():
    """Fix-R31D-4/R31B-1: ClinVar_search_variants' "query" param is
    documented as an alias for "condition" (a disease/phenotype search),
    not a gene lookup -- confirmed live that querying gene names through
    it only coincidentally matched conditions whose name happens to
    contain the gene symbol (e.g. 40 rows for HOXB13 vs the real 1943 via
    the dedicated "gene" param). The aggregator must use "gene" directly."""
    t = _tool()
    calls = []

    def fake_run_one_function(call):
        calls.append(call)
        if call["name"] == "ClinVar_search_variants":
            return {"status": "success", "data": {"total_count": 1943, "variants": []}}
        return {"status": "error", "error": "not used in this test"}

    with patch(
        "tooluniverse.execute_function.ToolUniverse.run_one_function",
        side_effect=fake_run_one_function,
    ), patch("tooluniverse.execute_function.ToolUniverse.load_tools", return_value=None):
        result = t.run({"gene": "HOXB13"})

    clinvar_call = next(c for c in calls if c["name"] == "ClinVar_search_variants")
    assert clinvar_call["arguments"] == {"gene": "HOXB13", "limit": 100}
    assert result["data"]["annotations"]["clinvar"]["total_gene_variants"] == 1943


def test_rsid_only_query_resolves_gene_via_dbsnp_before_other_sources():
    """Fix-R31B-1: ClinVar/CIViC/gnomAD/UniProt are all gene-keyed, none
    rsid-keyed (confirmed live: both ClinVar's "query" and "variant_id"
    params return 0 rows for a bare rsid like "rs671" -- variant_id is
    ClinVar's own internal numeric id, not a dbSNP rsid). An rsid-only
    request must resolve to a gene via dbSNP first so the other sources
    can still be queried, instead of silently skipping all of them."""
    t = _tool()
    calls = []

    def fake_run_one_function(call):
        calls.append(call)
        if call["name"] == "dbsnp_get_variant_by_rsid":
            return {
                "status": "success",
                "data": {"hgvs_notation": "...|GENE=ALDH2:217"},
            }
        if call["name"] == "gnomad_get_gene":
            return {"status": "success", "data": {"gene": {"gene_id": "ENSG00000111275"}}}
        return {"status": "success", "data": {}}

    with patch(
        "tooluniverse.execute_function.ToolUniverse.run_one_function",
        side_effect=fake_run_one_function,
    ), patch("tooluniverse.execute_function.ToolUniverse.load_tools", return_value=None):
        result = t.run({"rsid": "rs671"})

    called_names = [c["name"] for c in calls]
    assert "dbsnp_get_variant_by_rsid" in called_names
    assert "gnomad_get_gene" in called_names
    gnomad_call = next(c for c in calls if c["name"] == "gnomad_get_gene")
    assert gnomad_call["arguments"] == {"gene_symbol": "ALDH2"}
    assert result["data"]["annotations"]["gnomad"]["gene_id"] == "ENSG00000111275"


def test_resolve_gene_from_rsid_extracts_symbol_from_hgvs_notation():
    t = _tool()
    tu_mock_result = {
        "status": "success",
        "data": {"hgvs_notation": "HGVS=...|SEQ=[G/A]|LEN=1|GENE=ALDH2:217"},
    }

    class _FakeTU:
        def run_one_function(self, call):
            return tu_mock_result

    sources_failed = []
    gene, variant_tokens = t._resolve_gene_from_rsid(_FakeTU(), "rs671", sources_failed)
    assert gene == "ALDH2"
    assert variant_tokens is None
    assert sources_failed == []


def test_resolve_gene_from_rsid_records_failure_when_gene_not_found():
    t = _tool()

    class _FakeTU:
        def run_one_function(self, call):
            return {"status": "success", "data": {"hgvs_notation": "no gene marker here"}}

    sources_failed = []
    gene, variant_tokens = t._resolve_gene_from_rsid(_FakeTU(), "rs9999999", sources_failed)
    assert gene is None
    assert variant_tokens is None
    assert len(sources_failed) == 1


def test_resolve_gene_from_rsid_extracts_protein_change_tokens():
    """Fix-R48A-1: dbSNP's hgvs_notation already carries protein-change
    annotations (p.Lys329Glu etc.), but the resolver previously discarded
    everything except the gene symbol -- so an rsid-only query could NEVER
    produce a ClinVar/CIViC exact_match, even when the exact variant was
    present in the fetched results, because variant_token was only ever
    derived from an explicit 'variant' argument. Confirmed live for
    rs77931234 (ACADM, a real MCAD-deficiency founder variant, ClinVar
    VCV000003586 Pathogenic/Likely pathogenic) and rs113488022 (BRAF V600E,
    CIViC id 12) -- both now correctly extract p.Lys329Glu / p.Val600Glu."""
    t = _tool()

    class _FakeTU:
        def run_one_function(self, call):
            return {
                "status": "success",
                "data": {
                    "hgvs_notation": (
                        "HGVS=NM_000016.6:c.985A>C,NM_000016.6:c.985A>G,"
                        "NP_000007.1:p.Lys329Gln,NP_000007.1:p.Lys329Glu"
                        "|SEQ=[A/C/G]|LEN=1|GENE=ACADM:34"
                    )
                },
            }

    sources_failed = []
    gene, variant_tokens = t._resolve_gene_from_rsid(_FakeTU(), "rs77931234", sources_failed)
    assert gene == "ACADM"
    assert variant_tokens == ["Lys329Gln", "Lys329Glu"]
    # A multi-allelic site (this one has both A>C and A>G alternates) yields
    # multiple candidates; only the one matching the real record should hit.
    assert _title_matches("NM_000016.6(ACADM):c.985A>G (p.Lys329Glu)", variant_tokens)
    assert not _title_matches("NM_000016.6(ACADM):c.1184A>T (p.Lys395Ile)", variant_tokens)


def test_variant_match_forms_reverse_converts_3letter_to_short_form():
    """The 3-letter form dbSNP's hgvs_notation produces ('Lys329Glu') must
    also match short-form records like CIViC's ('K329E' / 'V600E'), not just
    ClinVar's own 3-letter-style titles -- confirmed live this was previously
    one-directional (short -> 3-letter only), so an rsid-derived token could
    resolve a ClinVar match but never a CIViC one."""
    forms = _variant_match_forms("Val600Glu")
    assert "val600glu" in forms
    assert "v600e" in forms
    assert _title_matches("V600E", "Val600Glu")
    assert _title_matches("V600E", ["Val600Gly", "Val600Glu"])


def test_rsid_only_query_derives_variant_token_for_exact_matching():
    """End-to-end: an rsid-only call must be able to reach exact_match=True
    against ClinVar when the variant is among the fetched rows -- previously
    impossible for ANY rsid-only query regardless of what ClinVar returned,
    since variant_token stayed None whenever 'variant' wasn't explicitly
    supplied."""
    t = _tool()
    calls = []

    def fake_run_one_function(call):
        calls.append(call)
        if call["name"] == "dbsnp_get_variant_by_rsid":
            return {
                "status": "success",
                "data": {
                    "hgvs_notation": "HGVS=...|NP_000007.1:p.Lys329Glu|GENE=ACADM:34"
                },
            }
        if call["name"] == "ClinVar_search_variants":
            return {
                "status": "success",
                "data": {
                    "total_count": 1127,
                    "variants": [
                        {
                            "title": "NM_000016.6(ACADM):c.985A>G (p.Lys329Glu)",
                            "clinical_significance": "Pathogenic/Likely pathogenic",
                        }
                    ],
                },
            }
        return {"status": "success", "data": {}}

    with patch(
        "tooluniverse.execute_function.ToolUniverse.run_one_function",
        side_effect=fake_run_one_function,
    ), patch("tooluniverse.execute_function.ToolUniverse.load_tools", return_value=None):
        result = t.run({"rsid": "rs77931234"})

    clinvar = result["data"]["annotations"]["clinvar"]
    assert clinvar["exact_match"] is True
    assert clinvar["matched"] == 1
    assert result["data"]["summary"]["clinvar_classification"] == "Pathogenic/Likely pathogenic"
