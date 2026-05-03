#!/usr/bin/env python3
"""
Comprehensive Test Suite for tooluniverse-variant-analysis

Tests VCF parsing, variant filtering, mutation classification, annotation,
and BixBench-style question answering.
"""

import os
import sys
import json
import traceback
from collections import Counter

# Add skill directory to path
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SKILL_DIR)

from python_implementation import (
    parse_vcf,
    parse_vcf_cyvcf2,
    classify_variant_type,
    classify_mutation_type_from_ref_alt,
    filter_variants,
    filter_non_reference_variants,
    filter_intronic_intergenic,
    compute_variant_statistics,
    compute_vaf_mutation_crosstab,
    fraction_of_vaf_filtered_by_mutation_type,
    compare_cohort_mutation_frequency,
    count_non_reference_after_filtering,
    variants_to_dataframe,
    variant_analysis_pipeline,
    answer_vaf_mutation_fraction,
    answer_cohort_comparison,
    answer_non_reference_after_filter,
    annotate_variant_with_myvariant,
    batch_annotate_variants,
    generate_variant_report,
    VCFData,
    VariantRecord,
    FilterCriteria,
    AnnotationResult,
    VariantAnalysisReport,
    CONSEQUENCE_TO_MUTATION_TYPE,
    INTRONIC_INTERGENIC_TERMS,
)

TEST_VCF = os.path.join(SKILL_DIR, "test_data", "sample.vcf")
TEST_VCF_COHORT2 = os.path.join(SKILL_DIR, "test_data", "cohort2.vcf")

# ---------------------------------------------------------------------------
# Test tracking
# ---------------------------------------------------------------------------
RESULTS = []


def run_test(name, func):
    """Run a test function and track results."""
    try:
        func()
        RESULTS.append(("PASS", name, ""))
        print(f"  PASS: {name}")
        return True
    except Exception as e:
        RESULTS.append(("FAIL", name, str(e)))
        print(f"  FAIL: {name}")
        print(f"        {e}")
        traceback.print_exc()
        return False


# ---------------------------------------------------------------------------
# Phase 1: VCF Parsing Tests
# ---------------------------------------------------------------------------

def test_parse_vcf_basic():
    """Test basic VCF parsing with pure Python parser."""
    vcf_data = parse_vcf(TEST_VCF)
    assert len(vcf_data.variants) == 24, f"Expected 24 variants, got {len(vcf_data.variants)}"
    assert len(vcf_data.samples) == 2, f"Expected 2 samples, got {len(vcf_data.samples)}"
    assert vcf_data.samples[0] == "SAMPLE1"
    assert vcf_data.samples[1] == "SAMPLE2"
    assert vcf_data.file_format == "VCFv4.2"
    assert len(vcf_data.parse_errors) == 0, f"Parse errors: {vcf_data.parse_errors}"


def test_parse_vcf_cyvcf2():
    """Test VCF parsing with cyvcf2 (fast parser)."""
    vcf_data = parse_vcf_cyvcf2(TEST_VCF)
    assert len(vcf_data.variants) == 24, f"Expected 24 variants, got {len(vcf_data.variants)}"
    assert len(vcf_data.samples) == 2


def test_parse_variant_fields():
    """Test individual variant field extraction."""
    vcf_data = parse_vcf(TEST_VCF)
    v0 = vcf_data.variants[0]
    assert v0.chrom == "1", f"Expected chrom 1, got {v0.chrom}"
    assert v0.pos == 12345, f"Expected pos 12345, got {v0.pos}"
    assert v0.ref == "A"
    assert v0.alt == "G"
    assert v0.vid == "rs12345"
    assert v0.qual == 100.0
    assert v0.filter_status == "PASS"


def test_parse_vaf_extraction():
    """Test VAF extraction from multiple formats."""
    vcf_data = parse_vcf(TEST_VCF)
    v0 = vcf_data.variants[0]
    # SAMPLE1 has AF=0.25 and AD=150,50 (50/200 = 0.25)
    assert "SAMPLE1" in v0.vaf, f"SAMPLE1 not in VAF: {v0.vaf}"
    assert abs(v0.vaf["SAMPLE1"] - 0.25) < 0.01, f"Expected VAF 0.25, got {v0.vaf['SAMPLE1']}"
    # SAMPLE2 has AF=0.05
    assert "SAMPLE2" in v0.vaf
    assert abs(v0.vaf["SAMPLE2"] - 0.05) < 0.01


def test_parse_depth_extraction():
    """Test depth extraction from VCF."""
    vcf_data = parse_vcf(TEST_VCF)
    v0 = vcf_data.variants[0]
    assert "SAMPLE1" in v0.depth
    assert v0.depth["SAMPLE1"] == 200


def test_parse_genotype_extraction():
    """Test genotype extraction."""
    vcf_data = parse_vcf(TEST_VCF)
    v0 = vcf_data.variants[0]
    assert v0.genotype.get("SAMPLE1") == "0/1"
    assert v0.genotype.get("SAMPLE2") == "0/0"


def test_parse_info_annotations():
    """Test annotation extraction from INFO field (SnpEff ANN)."""
    vcf_data = parse_vcf(TEST_VCF)
    v0 = vcf_data.variants[0]
    assert v0.consequence == "missense_variant", f"Got consequence: {v0.consequence}"
    assert v0.impact == "MODERATE", f"Got impact: {v0.impact}"
    assert v0.gene == "GENE1", f"Got gene: {v0.gene}"
    assert v0.mutation_type == "missense", f"Got mutation_type: {v0.mutation_type}"
    assert "p.Thr34Ala" in v0.protein_change


def test_parse_clinical_significance():
    """Test clinical significance extraction from INFO."""
    vcf_data = parse_vcf(TEST_VCF)
    # Variant at 1:12600 has CLNSIG=Likely_pathogenic
    v = [v for v in vcf_data.variants if v.pos == 12600 and v.chrom == "1"][0]
    assert "Likely" in v.clinical_significance or "pathogenic" in v.clinical_significance, \
        f"Expected Likely_pathogenic, got {v.clinical_significance}"


def test_parse_nonexistent_file():
    """Test parsing a non-existent file (error handling)."""
    vcf_data = parse_vcf("/nonexistent/path/test.vcf")
    assert len(vcf_data.parse_errors) > 0
    assert "not found" in vcf_data.parse_errors[0].lower()


def test_parse_max_variants():
    """Test max_variants limit."""
    vcf_data = parse_vcf(TEST_VCF, max_variants=5)
    assert len(vcf_data.variants) == 5


# ---------------------------------------------------------------------------
# Phase 2: Variant Classification Tests
# ---------------------------------------------------------------------------

def test_classify_variant_type_snv():
    """Test SNV classification."""
    assert classify_variant_type("A", "G") == "SNV"
    assert classify_variant_type("C", "T") == "SNV"


def test_classify_variant_type_insertion():
    """Test insertion classification."""
    assert classify_variant_type("A", "AT") == "INS"
    assert classify_variant_type("G", "GAAAA") == "INS"


def test_classify_variant_type_deletion():
    """Test deletion classification."""
    assert classify_variant_type("AT", "A") == "DEL"
    assert classify_variant_type("AGC", "A") == "DEL"


def test_classify_variant_type_mnv():
    """Test MNV classification."""
    assert classify_variant_type("AT", "GC") == "MNV"


def test_classify_variant_type_complex():
    """Test complex variant classification."""
    assert classify_variant_type("AGC", "TG") == "COMPLEX"


def test_mutation_type_mapping():
    """Test consequence to mutation type mapping."""
    from python_implementation import _consequence_to_mutation_type
    assert _consequence_to_mutation_type("missense_variant") == "missense"
    assert _consequence_to_mutation_type("stop_gained") == "nonsense"
    assert _consequence_to_mutation_type("frameshift_variant") == "frameshift"
    assert _consequence_to_mutation_type("synonymous_variant") == "synonymous"
    assert _consequence_to_mutation_type("intron_variant") == "intronic"
    assert _consequence_to_mutation_type("intergenic_variant") == "intergenic"
    assert _consequence_to_mutation_type("splice_acceptor_variant") == "splice_site"
    assert _consequence_to_mutation_type("inframe_deletion") == "inframe_deletion"
    assert _consequence_to_mutation_type("5_prime_UTR_variant") == "UTR_5"
    assert _consequence_to_mutation_type("3_prime_UTR_variant") == "UTR_3"


def test_mutation_type_gatk_style():
    """Test GATK Funcotator-style consequence mapping."""
    from python_implementation import _consequence_to_mutation_type
    assert _consequence_to_mutation_type("MISSENSE") == "missense"
    assert _consequence_to_mutation_type("NONSENSE") == "nonsense"
    assert _consequence_to_mutation_type("SILENT") == "synonymous"
    assert _consequence_to_mutation_type("INTRON") == "intronic"


def test_mutation_type_combined():
    """Test combined consequence types."""
    from python_implementation import _consequence_to_mutation_type
    assert _consequence_to_mutation_type("missense_variant&splice_region_variant") == "missense"


def test_all_variants_have_type():
    """Test that all parsed variants have variant_type set."""
    vcf_data = parse_vcf(TEST_VCF)
    for v in vcf_data.variants:
        assert v.variant_type in ("SNV", "INS", "DEL", "MNV", "COMPLEX", "NO_ALT"), \
            f"Missing variant_type for {v.key}: {v.variant_type}"


def test_all_annotated_variants_have_mutation_type():
    """Test that annotated variants have mutation_type."""
    vcf_data = parse_vcf(TEST_VCF)
    annotated = [v for v in vcf_data.variants if v.consequence]
    assert len(annotated) > 0, "No annotated variants found"
    for v in annotated:
        assert v.mutation_type, f"Missing mutation_type for {v.key} (consequence={v.consequence})"


# ---------------------------------------------------------------------------
# Phase 3: Filtering Tests
# ---------------------------------------------------------------------------

def test_filter_by_vaf():
    """Test VAF filtering."""
    vcf_data = parse_vcf(TEST_VCF)
    criteria = FilterCriteria(min_vaf=0.20, sample="SAMPLE1")
    passing, failing = filter_variants(vcf_data.variants, criteria)
    assert len(passing) > 0
    for v in passing:
        if "SAMPLE1" in v.vaf:
            assert v.vaf["SAMPLE1"] >= 0.20, f"VAF {v.vaf['SAMPLE1']} below 0.20"


def test_filter_by_max_vaf():
    """Test max VAF filtering."""
    vcf_data = parse_vcf(TEST_VCF)
    criteria = FilterCriteria(max_vaf=0.30, sample="SAMPLE1")
    passing, failing = filter_variants(vcf_data.variants, criteria)
    assert len(passing) > 0
    for v in passing:
        if "SAMPLE1" in v.vaf:
            assert v.vaf["SAMPLE1"] <= 0.30, f"VAF {v.vaf['SAMPLE1']} above 0.30"


def test_filter_by_depth():
    """Test depth filtering."""
    vcf_data = parse_vcf(TEST_VCF)
    criteria = FilterCriteria(min_depth=200, sample="SAMPLE1")
    passing, failing = filter_variants(vcf_data.variants, criteria)
    assert len(passing) > 0
    for v in passing:
        if "SAMPLE1" in v.depth:
            assert v.depth["SAMPLE1"] >= 200


def test_filter_by_quality():
    """Test quality filtering."""
    vcf_data = parse_vcf(TEST_VCF)
    criteria = FilterCriteria(min_qual=100)
    passing, failing = filter_variants(vcf_data.variants, criteria)
    for v in passing:
        assert v.qual >= 100


def test_filter_pass_only():
    """Test PASS-only filtering."""
    vcf_data = parse_vcf(TEST_VCF)
    criteria = FilterCriteria(pass_only=True)
    passing, failing = filter_variants(vcf_data.variants, criteria)
    for v in passing:
        assert v.filter_status in ("PASS", ".", "")


def test_filter_by_variant_type():
    """Test variant type filtering."""
    vcf_data = parse_vcf(TEST_VCF)
    criteria = FilterCriteria(variant_types=["SNV"])
    passing, failing = filter_variants(vcf_data.variants, criteria)
    for v in passing:
        assert v.variant_type == "SNV"


def test_filter_by_mutation_type():
    """Test mutation type filtering."""
    vcf_data = parse_vcf(TEST_VCF)
    criteria = FilterCriteria(mutation_types=["missense"])
    passing, failing = filter_variants(vcf_data.variants, criteria)
    assert len(passing) > 0
    for v in passing:
        assert "missense" in v.mutation_type.lower(), f"Expected missense, got {v.mutation_type}"


def test_filter_exclude_consequences():
    """Test consequence exclusion filtering."""
    vcf_data = parse_vcf(TEST_VCF)
    criteria = FilterCriteria(exclude_consequences=["intronic", "intergenic", "upstream", "downstream"])
    passing, failing = filter_variants(vcf_data.variants, criteria)
    for v in passing:
        mt = v.mutation_type.lower()
        assert "intronic" not in mt and "intergenic" not in mt and "upstream" not in mt and "downstream" not in mt, \
            f"Should be excluded: {v.mutation_type}"


def test_filter_by_chromosome():
    """Test chromosome filtering."""
    vcf_data = parse_vcf(TEST_VCF)
    criteria = FilterCriteria(chromosomes=["7"])
    passing, failing = filter_variants(vcf_data.variants, criteria)
    for v in passing:
        assert v.chrom == "7"


def test_filter_combined():
    """Test combined filters."""
    vcf_data = parse_vcf(TEST_VCF)
    criteria = FilterCriteria(
        min_vaf=0.10,
        max_vaf=0.50,
        min_depth=100,
        pass_only=True,
        variant_types=["SNV"],
        sample="SAMPLE1",
    )
    passing, failing = filter_variants(vcf_data.variants, criteria)
    assert len(passing) > 0
    for v in passing:
        assert v.variant_type == "SNV"
        assert v.filter_status in ("PASS", ".", "")


def test_filter_non_reference():
    """Test non-reference variant filtering."""
    vcf_data = parse_vcf(TEST_VCF)
    non_ref = filter_non_reference_variants(vcf_data.variants)
    # Variant at 1:13000 has GT=0/0 for both samples, should be filtered
    keys = [v.key for v in non_ref]
    assert "1:13000:G>A" not in keys, "Hom-ref variant should be filtered"


def test_filter_intronic_intergenic():
    """Test intronic/intergenic filtering."""
    vcf_data = parse_vcf(TEST_VCF)
    passing, excluded = filter_intronic_intergenic(vcf_data.variants)
    # Purely intronic/intergenic/upstream/downstream should be excluded
    pure_terms = {'intronic', 'intergenic', 'upstream', 'downstream'}
    for v in excluded:
        mt = v.mutation_type.lower()
        consequence = v.consequence.lower() if v.consequence else ""
        assert mt in pure_terms or consequence in {
            'intron_variant', 'intergenic_variant',
            'upstream_gene_variant', 'downstream_gene_variant',
        }, f"Incorrectly excluded: {v.mutation_type} ({v.consequence})"
    # splice_region should NOT be excluded
    for v in passing:
        mt = v.mutation_type.lower()
        assert mt not in {'intronic', 'intergenic'}, \
            f"Should have been excluded: {v.mutation_type}"


# ---------------------------------------------------------------------------
# Phase 4: Statistics Tests
# ---------------------------------------------------------------------------

def test_compute_statistics():
    """Test comprehensive statistics computation."""
    vcf_data = parse_vcf(TEST_VCF)
    stats = compute_variant_statistics(vcf_data.variants, vcf_data.samples)
    assert stats['total_variants'] == 24
    assert 'SNV' in stats['variant_types']
    assert 'INS' in stats['variant_types']
    assert 'DEL' in stats['variant_types']
    assert stats['ti_tv_ratio'] is not None


def test_vaf_mutation_crosstab():
    """Test VAF vs mutation type cross-tabulation."""
    vcf_data = parse_vcf(TEST_VCF)
    ct = compute_vaf_mutation_crosstab(vcf_data.variants, sample="SAMPLE1")
    assert 'vaf_bins' in ct
    assert 'mutation_types' in ct
    assert 'crosstab' in ct
    assert len(ct['vaf_bins']) == 6


def test_ti_tv_ratio():
    """Test transition/transversion ratio calculation."""
    vcf_data = parse_vcf(TEST_VCF)
    stats = compute_variant_statistics(vcf_data.variants)
    assert stats['ti_tv_ratio'] is not None
    assert stats['ti_tv_ratio'] > 0


def test_per_sample_vaf_stats():
    """Test per-sample VAF statistics."""
    vcf_data = parse_vcf(TEST_VCF)
    stats = compute_variant_statistics(vcf_data.variants, vcf_data.samples)
    assert "SAMPLE1" in stats['vaf_stats']
    s1_stats = stats['vaf_stats']['SAMPLE1']
    assert 'mean' in s1_stats
    assert 'median' in s1_stats
    assert s1_stats['min'] >= 0
    assert s1_stats['max'] <= 1.0


# ---------------------------------------------------------------------------
# Phase 5: BixBench-style Question Tests
# ---------------------------------------------------------------------------

def test_bixbench_vaf_mutation_fraction():
    """
    BixBench Q: "What fraction of variants with VAF < 0.3 are annotated as missense mutations?"
    """
    result = answer_vaf_mutation_fraction(
        TEST_VCF, max_vaf=0.3, mutation_type="missense", sample="SAMPLE1",
        use_cyvcf2=False,
    )
    assert result['total_below_vaf'] > 0, "Should have variants below VAF 0.3"
    assert result['matching_mutation_type'] >= 0
    assert 0 <= result['fraction'] <= 1.0
    assert result['vaf_threshold'] == 0.3
    assert result['mutation_type'] == "missense"
    print(f"    Fraction of VAF<0.3 that are missense: {result['fraction']:.4f} "
          f"({result['matching_mutation_type']}/{result['total_below_vaf']})")


def test_bixbench_cohort_comparison():
    """
    BixBench Q: "What is the difference in missense variant frequency between cohorts?"
    """
    result = answer_cohort_comparison(
        [TEST_VCF, TEST_VCF_COHORT2],
        mutation_type="missense",
        cohort_names=["Cohort_A", "Cohort_B"],
        use_cyvcf2=False,
    )
    assert "Cohort_A" in result['cohorts']
    assert "Cohort_B" in result['cohorts']
    assert result['frequency_difference'] is not None
    assert result['frequency_difference'] >= 0
    ca = result['cohorts']['Cohort_A']
    cb = result['cohorts']['Cohort_B']
    print(f"    Cohort_A missense freq: {ca['frequency']:.4f} ({ca['matching_variants']}/{ca['total_variants']})")
    print(f"    Cohort_B missense freq: {cb['frequency']:.4f} ({cb['matching_variants']}/{cb['total_variants']})")
    print(f"    Difference: {result['frequency_difference']:.4f}")


def test_bixbench_non_reference_after_filter():
    """
    BixBench Q: "After filtering intronic/intergenic variants, how many non-reference variants remain?"
    """
    result = answer_non_reference_after_filter(
        TEST_VCF,
        exclude_intronic_intergenic=True,
        use_cyvcf2=False,
    )
    assert result['total_input'] == 24
    assert result['non_reference'] > 0
    assert result['remaining'] > 0
    assert result['remaining'] <= result['non_reference']
    assert result['excluded_intronic_intergenic'] >= 0
    print(f"    Total: {result['total_input']}, Non-ref: {result['non_reference']}, "
          f"Excluded: {result['excluded_intronic_intergenic']}, Remaining: {result['remaining']}")


def test_bixbench_vaf_range_mutation():
    """
    BixBench Q variant: "What fraction of variants with VAF between 0.1 and 0.3 are synonymous?"
    """
    vcf_data = parse_vcf(TEST_VCF)
    # Filter to VAF range
    criteria = FilterCriteria(min_vaf=0.1, max_vaf=0.3, sample="SAMPLE1")
    passing, _ = filter_variants(vcf_data.variants, criteria)
    # Now count synonymous
    total = len(passing)
    syn = sum(1 for v in passing if v.mutation_type == "synonymous")
    frac = syn / total if total > 0 else 0
    assert total > 0, "Should have variants in VAF 0.1-0.3"
    print(f"    Fraction of VAF 0.1-0.3 that are synonymous: {frac:.4f} ({syn}/{total})")


def test_bixbench_high_impact_count():
    """
    BixBench Q: "How many high-impact variants are there?"
    """
    vcf_data = parse_vcf(TEST_VCF)
    high_impact = [v for v in vcf_data.variants if v.impact == "HIGH"]
    assert len(high_impact) > 0, "Should have HIGH impact variants"
    print(f"    High impact variants: {len(high_impact)}")
    for v in high_impact:
        print(f"      {v.key} - {v.gene} - {v.consequence}")


def test_bixbench_missense_per_gene():
    """
    BixBench Q: "Which gene has the most missense variants?"
    """
    vcf_data = parse_vcf(TEST_VCF)
    missense = [v for v in vcf_data.variants if v.mutation_type == "missense"]
    gene_counts = Counter(v.gene for v in missense if v.gene)
    assert len(gene_counts) > 0
    top_gene, top_count = gene_counts.most_common(1)[0]
    print(f"    Top gene by missense: {top_gene} ({top_count} variants)")
    for gene, count in gene_counts.most_common(5):
        print(f"      {gene}: {count}")


def test_bixbench_filter_then_count():
    """
    BixBench Q: "After removing variants with depth < 100 and VAF < 0.1, how many missense remain?"
    """
    vcf_data = parse_vcf(TEST_VCF)
    criteria = FilterCriteria(min_depth=100, min_vaf=0.1, sample="SAMPLE1")
    passing, _ = filter_variants(vcf_data.variants, criteria)
    missense = [v for v in passing if v.mutation_type == "missense"]
    print(f"    After filter (DP>=100, VAF>=0.1): {len(passing)} variants, {len(missense)} missense")
    assert len(passing) > 0


def test_bixbench_clinical_variants():
    """
    BixBench Q: "How many variants have clinical significance annotations?"
    """
    vcf_data = parse_vcf(TEST_VCF)
    clinical = [v for v in vcf_data.variants if v.clinical_significance]
    assert len(clinical) > 0, "Should have clinically significant variants"
    print(f"    Clinical variants: {len(clinical)}")
    for v in clinical:
        print(f"      {v.key} - {v.gene} - {v.clinical_significance}")


def test_bixbench_variant_type_distribution():
    """
    BixBench Q: "What is the distribution of variant types (SNV, indel)?"
    """
    vcf_data = parse_vcf(TEST_VCF)
    stats = compute_variant_statistics(vcf_data.variants)
    assert 'SNV' in stats['variant_types']
    total = stats['total_variants']
    print(f"    Variant type distribution:")
    for vt, count in stats['variant_types'].most_common():
        print(f"      {vt}: {count} ({100*count/total:.1f}%)")


def test_bixbench_sample_comparison():
    """
    BixBench Q: "Compare variant counts between samples."
    """
    vcf_data = parse_vcf(TEST_VCF)
    sample_variant_counts = {}
    for sample in vcf_data.samples:
        non_ref = 0
        for v in vcf_data.variants:
            gt = v.genotype.get(sample, "0/0")
            alleles = gt.replace('|', '/').split('/')
            if any(a != '0' and a != '.' for a in alleles):
                non_ref += 1
        sample_variant_counts[sample] = non_ref
    print(f"    Per-sample non-ref counts:")
    for sample, count in sample_variant_counts.items():
        print(f"      {sample}: {count}")
    assert sample_variant_counts.get("SAMPLE1", 0) > sample_variant_counts.get("SAMPLE2", 0)


# ---------------------------------------------------------------------------
# Phase 6: DataFrame Tests
# ---------------------------------------------------------------------------

def test_dataframe_conversion():
    """Test variants to DataFrame conversion."""
    vcf_data = parse_vcf(TEST_VCF)
    df = variants_to_dataframe(vcf_data.variants, sample="SAMPLE1")
    assert len(df) == 24
    assert 'chrom' in df.columns
    assert 'pos' in df.columns
    assert 'ref' in df.columns
    assert 'alt' in df.columns
    assert 'vaf' in df.columns
    assert 'mutation_type' in df.columns
    assert 'gene' in df.columns


def test_dataframe_filtering():
    """Test filtering via DataFrame (pandas-based workflow)."""
    vcf_data = parse_vcf(TEST_VCF)
    df = variants_to_dataframe(vcf_data.variants, sample="SAMPLE1")
    # Filter missense with VAF >= 0.2
    filtered = df[(df['mutation_type'] == 'missense') & (df['vaf'] >= 0.2)]
    assert len(filtered) > 0


def test_dataframe_aggregation():
    """Test aggregation via DataFrame."""
    vcf_data = parse_vcf(TEST_VCF)
    df = variants_to_dataframe(vcf_data.variants, sample="SAMPLE1")
    # Count by mutation type
    counts = df['mutation_type'].value_counts()
    assert 'missense' in counts.index


# ---------------------------------------------------------------------------
# Phase 7: Report Generation Tests
# ---------------------------------------------------------------------------

def test_generate_report():
    """Test markdown report generation."""
    vcf_data = parse_vcf(TEST_VCF)
    output_file = os.path.join(SKILL_DIR, "test_data", "test_report.md")
    path = generate_variant_report(vcf_data, output_file=output_file)
    assert os.path.exists(path), f"Report file not created: {path}"
    with open(path, 'r') as f:
        content = f.read()
    assert "Variant Analysis Report" in content
    assert "Summary Statistics" in content
    assert "Chromosome Distribution" in content
    # Cleanup
    os.remove(path)


def test_full_pipeline():
    """Test complete analysis pipeline."""
    output_file = os.path.join(SKILL_DIR, "test_data", "test_pipeline_report.md")
    criteria = FilterCriteria(min_vaf=0.10, sample="SAMPLE1")
    report = variant_analysis_pipeline(
        vcf_path=TEST_VCF,
        output_file=output_file,
        filters=criteria,
        annotate=False,
        use_cyvcf2=False,
    )
    assert report.total_variants == 24
    assert report.total_samples == 2
    assert os.path.exists(output_file)
    # Cleanup
    os.remove(output_file)


# ---------------------------------------------------------------------------
# Phase 8: ToolUniverse Annotation Tests (requires network)
# ---------------------------------------------------------------------------

def test_annotation_myvariant():
    """Test MyVariant.info annotation via ToolUniverse."""
    try:
        from tooluniverse import ToolUniverse
        tu = ToolUniverse()
        tu.load_tools()
    except Exception as e:
        print(f"    SKIP: ToolUniverse not available: {e}")
        return

    # Create a variant for rs7412 (APOE)
    v = VariantRecord(
        chrom="19", pos=44908822, ref="C", alt="T",
        vid="rs7412"
    )
    ann = annotate_variant_with_myvariant(tu, v)
    assert ann.gene_symbol == "APOE", f"Expected APOE, got {ann.gene_symbol}"
    assert ann.dbsnp_rsid == "rs7412", f"Expected rs7412, got {ann.dbsnp_rsid}"
    assert ann.cadd_phred is not None, "CADD score should be available"
    assert ann.gnomad_af is not None, "gnomAD AF should be available"
    print(f"    APOE rs7412: CADD={ann.cadd_phred}, gnomAD_AF={ann.gnomad_af:.4f}, "
          f"ClinVar={ann.clinvar_classification}")


def test_annotation_batch():
    """Test batch annotation."""
    try:
        from tooluniverse import ToolUniverse
        tu = ToolUniverse()
        tu.load_tools()
    except Exception as e:
        print(f"    SKIP: ToolUniverse not available: {e}")
        return

    vcf_data = parse_vcf(TEST_VCF)
    # Only annotate variants with rsIDs
    rsid_variants = [v for v in vcf_data.variants if v.vid and v.vid.startswith('rs')][:5]
    annotations = batch_annotate_variants(
        tu, rsid_variants,
        use_myvariant=True,
        max_annotate=5,
    )
    assert len(annotations) == len(rsid_variants)
    annotated_count = sum(1 for a in annotations if a.gene_symbol)
    print(f"    Batch annotated: {annotated_count}/{len(annotations)} variants with gene info")


def test_annotation_updates_variant():
    """Test that annotation updates the original variant record."""
    try:
        from tooluniverse import ToolUniverse
        tu = ToolUniverse()
        tu.load_tools()
    except Exception as e:
        print(f"    SKIP: ToolUniverse not available: {e}")
        return

    v = VariantRecord(
        chrom="19", pos=44908822, ref="C", alt="T",
        vid="rs7412"
    )
    assert not v.gene  # Gene not set yet
    batch_annotate_variants(tu, [v], use_myvariant=True, max_annotate=1)
    assert v.gene == "APOE", f"Expected APOE, got {v.gene}"


# ---------------------------------------------------------------------------
# Phase 9: Edge Cases
# ---------------------------------------------------------------------------

def test_empty_vcf():
    """Test handling of empty/minimal VCF."""
    # Create temp minimal VCF
    temp_vcf = os.path.join(SKILL_DIR, "test_data", "empty.vcf")
    with open(temp_vcf, 'w') as f:
        f.write("##fileformat=VCFv4.2\n")
        f.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n")
    vcf_data = parse_vcf(temp_vcf)
    assert len(vcf_data.variants) == 0
    assert len(vcf_data.samples) == 0
    stats = compute_variant_statistics(vcf_data.variants)
    assert stats['total_variants'] == 0
    os.remove(temp_vcf)


def test_multiallelic():
    """Test handling of multi-allelic variants."""
    temp_vcf = os.path.join(SKILL_DIR, "test_data", "multi.vcf")
    with open(temp_vcf, 'w') as f:
        f.write("##fileformat=VCFv4.2\n")
        f.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE\n")
        f.write("1\t100\t.\tA\tG,T\t50\tPASS\t.\tGT:AD:DP\t0/1:50,30,20:100\n")
    vcf_data = parse_vcf(temp_vcf)
    assert len(vcf_data.variants) == 1
    v = vcf_data.variants[0]
    assert "G" in v.alt
    assert v.variant_type == "SNV"  # First alt is SNV
    os.remove(temp_vcf)


def test_no_vaf_available():
    """Test variants without VAF information."""
    temp_vcf = os.path.join(SKILL_DIR, "test_data", "novaf.vcf")
    with open(temp_vcf, 'w') as f:
        f.write("##fileformat=VCFv4.2\n")
        f.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE\n")
        f.write("1\t100\t.\tA\tG\t50\tPASS\t.\tGT\t0/1\n")
    vcf_data = parse_vcf(temp_vcf)
    v = vcf_data.variants[0]
    assert len(v.vaf) == 0  # No VAF data
    # Filtering should still work (skip VAF check)
    criteria = FilterCriteria(min_vaf=0.1)
    passing, _ = filter_variants(vcf_data.variants, criteria)
    os.remove(temp_vcf)


def test_consequence_to_mutation_type_coverage():
    """Test that common consequence terms are all mapped."""
    important_terms = [
        'missense_variant', 'stop_gained', 'frameshift_variant',
        'synonymous_variant', 'intron_variant', 'intergenic_variant',
        'splice_acceptor_variant', 'splice_donor_variant',
        'inframe_insertion', 'inframe_deletion',
        '5_prime_UTR_variant', '3_prime_UTR_variant',
        'upstream_gene_variant', 'downstream_gene_variant',
    ]
    for term in important_terms:
        assert term in CONSEQUENCE_TO_MUTATION_TYPE, f"Missing mapping for {term}"


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run_all_tests():
    """Run all tests and generate report."""
    print("=" * 80)
    print("VARIANT ANALYSIS SKILL - COMPREHENSIVE TEST SUITE")
    print("=" * 80)

    test_groups = [
        ("Phase 1: VCF Parsing", [
            ("Parse VCF basic", test_parse_vcf_basic),
            ("Parse VCF cyvcf2", test_parse_vcf_cyvcf2),
            ("Parse variant fields", test_parse_variant_fields),
            ("Parse VAF extraction", test_parse_vaf_extraction),
            ("Parse depth extraction", test_parse_depth_extraction),
            ("Parse genotype extraction", test_parse_genotype_extraction),
            ("Parse INFO annotations", test_parse_info_annotations),
            ("Parse clinical significance", test_parse_clinical_significance),
            ("Parse nonexistent file", test_parse_nonexistent_file),
            ("Parse max variants", test_parse_max_variants),
        ]),
        ("Phase 2: Variant Classification", [
            ("Classify SNV", test_classify_variant_type_snv),
            ("Classify insertion", test_classify_variant_type_insertion),
            ("Classify deletion", test_classify_variant_type_deletion),
            ("Classify MNV", test_classify_variant_type_mnv),
            ("Classify complex", test_classify_variant_type_complex),
            ("Mutation type mapping", test_mutation_type_mapping),
            ("GATK-style mapping", test_mutation_type_gatk_style),
            ("Combined consequence", test_mutation_type_combined),
            ("All variants have type", test_all_variants_have_type),
            ("Annotated variants have mutation type", test_all_annotated_variants_have_mutation_type),
        ]),
        ("Phase 3: Filtering", [
            ("Filter by VAF", test_filter_by_vaf),
            ("Filter by max VAF", test_filter_by_max_vaf),
            ("Filter by depth", test_filter_by_depth),
            ("Filter by quality", test_filter_by_quality),
            ("Filter PASS only", test_filter_pass_only),
            ("Filter by variant type", test_filter_by_variant_type),
            ("Filter by mutation type", test_filter_by_mutation_type),
            ("Filter exclude consequences", test_filter_exclude_consequences),
            ("Filter by chromosome", test_filter_by_chromosome),
            ("Filter combined", test_filter_combined),
            ("Filter non-reference", test_filter_non_reference),
            ("Filter intronic/intergenic", test_filter_intronic_intergenic),
        ]),
        ("Phase 4: Statistics", [
            ("Compute statistics", test_compute_statistics),
            ("VAF mutation crosstab", test_vaf_mutation_crosstab),
            ("Ti/Tv ratio", test_ti_tv_ratio),
            ("Per-sample VAF stats", test_per_sample_vaf_stats),
        ]),
        ("Phase 5: BixBench Questions", [
            ("VAF mutation fraction", test_bixbench_vaf_mutation_fraction),
            ("Cohort comparison", test_bixbench_cohort_comparison),
            ("Non-reference after filter", test_bixbench_non_reference_after_filter),
            ("VAF range mutation", test_bixbench_vaf_range_mutation),
            ("High impact count", test_bixbench_high_impact_count),
            ("Missense per gene", test_bixbench_missense_per_gene),
            ("Filter then count", test_bixbench_filter_then_count),
            ("Clinical variants", test_bixbench_clinical_variants),
            ("Variant type distribution", test_bixbench_variant_type_distribution),
            ("Sample comparison", test_bixbench_sample_comparison),
        ]),
        ("Phase 6: DataFrame", [
            ("DataFrame conversion", test_dataframe_conversion),
            ("DataFrame filtering", test_dataframe_filtering),
            ("DataFrame aggregation", test_dataframe_aggregation),
        ]),
        ("Phase 7: Report Generation", [
            ("Generate report", test_generate_report),
            ("Full pipeline", test_full_pipeline),
        ]),
        ("Phase 8: ToolUniverse Annotation", [
            ("MyVariant annotation", test_annotation_myvariant),
            ("Batch annotation", test_annotation_batch),
            ("Annotation updates variant", test_annotation_updates_variant),
        ]),
        ("Phase 9: Edge Cases", [
            ("Empty VCF", test_empty_vcf),
            ("Multi-allelic", test_multiallelic),
            ("No VAF available", test_no_vaf_available),
            ("Consequence mapping coverage", test_consequence_to_mutation_type_coverage),
        ]),
    ]

    total_pass = 0
    total_fail = 0

    for group_name, tests in test_groups:
        print(f"\n{'='*60}")
        print(f"  {group_name}")
        print(f"{'='*60}")
        for test_name, test_func in tests:
            if run_test(test_name, test_func):
                total_pass += 1
            else:
                total_fail += 1

    # Summary
    total = total_pass + total_fail
    print(f"\n{'='*80}")
    print(f"TEST SUMMARY")
    print(f"{'='*80}")
    print(f"  Passed: {total_pass}/{total}")
    print(f"  Failed: {total_fail}/{total}")
    print(f"  Success Rate: {100*total_pass/total:.1f}%")

    if total_fail == 0:
        print(f"\n  ALL TESTS PASSED! Skill is production-ready.")
    else:
        print(f"\n  {total_fail} test(s) failed. Review errors above.")
        for status, name, error in RESULTS:
            if status == "FAIL":
                print(f"    FAIL: {name} - {error}")

    return total_pass, total_fail


if __name__ == "__main__":
    passed, failed = run_all_tests()
    sys.exit(0 if failed == 0 else 1)
