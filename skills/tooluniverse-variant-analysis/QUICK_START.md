# Quick Start: Variant Analysis and Annotation

Parse VCF files, classify mutations, filter variants, annotate with clinical databases, and answer bioinformatics questions -- all in a few lines of code.

---

## Choose Your Implementation

### Python SDK

#### Option 1: Complete Pipeline (Recommended)

```python
from skills.tooluniverse_variant_analysis.python_implementation import (
    variant_analysis_pipeline,
    FilterCriteria,
)

# Basic analysis with report
report = variant_analysis_pipeline(
    vcf_path="input.vcf",
    output_file="analysis_report.md",
)

# Filtered analysis with ToolUniverse annotation
report = variant_analysis_pipeline(
    vcf_path="input.vcf",
    output_file="filtered_report.md",
    filters=FilterCriteria(
        min_vaf=0.10,
        min_depth=20,
        pass_only=True,
        sample="TUMOR",
    ),
    annotate=True,
    max_annotate=50,
)

print(f"Total variants: {report.total_variants}")
print(f"Variants by type: {report.variants_by_type}")
print(f"Variants by mutation type: {report.variants_by_mutation_type}")
```

#### Option 2: Answer Specific Questions

```python
from skills.tooluniverse_variant_analysis.python_implementation import (
    answer_vaf_mutation_fraction,
    answer_cohort_comparison,
    answer_non_reference_after_filter,
)

# Q: "What fraction of variants with VAF < 0.3 are missense?"
result = answer_vaf_mutation_fraction(
    vcf_path="input.vcf",
    max_vaf=0.3,
    mutation_type="missense",
    sample="TUMOR",
)
print(f"Fraction: {result['fraction']:.4f} ({result['matching_mutation_type']}/{result['total_below_vaf']})")

# Q: "Difference in missense frequency between cohorts?"
result = answer_cohort_comparison(
    vcf_paths=["cohort1.vcf", "cohort2.vcf"],
    mutation_type="missense",
    cohort_names=["Treatment", "Control"],
)
print(f"Difference: {result['frequency_difference']:.4f}")

# Q: "How many non-reference variants after removing intronic/intergenic?"
result = answer_non_reference_after_filter("input.vcf")
print(f"Remaining: {result['remaining']} (from {result['total_input']})")
```

#### Option 3: Individual Tools

```python
from skills.tooluniverse_variant_analysis.python_implementation import (
    parse_vcf,
    parse_vcf_cyvcf2,
    filter_variants,
    filter_intronic_intergenic,
    filter_non_reference_variants,
    compute_variant_statistics,
    compute_vaf_mutation_crosstab,
    variants_to_dataframe,
    batch_annotate_variants,
    generate_variant_report,
    FilterCriteria,
)

# Parse
vcf_data = parse_vcf("input.vcf")  # or parse_vcf_cyvcf2 for speed
print(f"Samples: {vcf_data.samples}")
print(f"Variants: {len(vcf_data.variants)}")

# Filter
criteria = FilterCriteria(min_vaf=0.05, min_depth=10, pass_only=True)
passing, failing = filter_variants(vcf_data.variants, criteria)

# Remove intronic/intergenic
coding, non_coding = filter_intronic_intergenic(passing)

# Statistics
stats = compute_variant_statistics(coding)
print(f"Missense: {stats['mutation_types'].get('missense', 0)}")
print(f"Ti/Tv: {stats['ti_tv_ratio']}")

# Cross-tabulation
ct = compute_vaf_mutation_crosstab(vcf_data.variants, sample="TUMOR")

# DataFrame for advanced analysis
df = variants_to_dataframe(vcf_data.variants, sample="TUMOR")
missense_high_vaf = df[(df['mutation_type'] == 'missense') & (df['vaf'] >= 0.3)]

# Annotate with ToolUniverse
from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()
annotations = batch_annotate_variants(tu, vcf_data.variants[:50])
```

---

### MCP (Model Context Protocol)

#### Conversational

```
"Parse this VCF file and tell me how many missense variants have VAF below 0.3"

"Compare the missense variant frequency between these two cohort VCFs"

"After removing intronic and intergenic variants, how many non-reference variants remain?"

"Annotate the top 20 variants in this VCF with ClinVar and gnomAD data"

"What is the Ti/Tv ratio and variant type distribution?"
```

#### With File Path

```
"Analyze /path/to/variants.vcf:
 - Filter to PASS variants with VAF >= 0.1
 - Show mutation type distribution
 - Generate a report"
```

---

## Tool Parameters (All Implementations)

### VCF Parsing

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `vcf_path` | string | Yes | Path to VCF file (.vcf or .vcf.gz) |
| `max_variants` | int | No | Maximum variants to parse (0 = all) |

### Filter Criteria

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `min_vaf` | float | No | Minimum VAF threshold |
| `max_vaf` | float | No | Maximum VAF threshold |
| `min_depth` | int | No | Minimum read depth |
| `min_qual` | float | No | Minimum QUAL score |
| `pass_only` | bool | No | Only PASS/. variants |
| `variant_types` | list | No | Include only: "SNV", "INS", "DEL", "MNV" |
| `mutation_types` | list | No | Include only: "missense", "nonsense", "synonymous", etc. |
| `exclude_consequences` | list | No | Exclude: "intronic", "intergenic", etc. |
| `chromosomes` | list | No | Include only: "1", "7", "17", etc. |
| `sample` | string | No | Sample name for multi-sample VCFs |

### BixBench Question Functions

| Function | Parameters | Returns |
|----------|-----------|---------|
| `answer_vaf_mutation_fraction` | `vcf_path`, `max_vaf`, `mutation_type`, `sample` | `{fraction, total_below_vaf, matching_mutation_type}` |
| `answer_cohort_comparison` | `vcf_paths`, `mutation_type`, `cohort_names` | `{cohorts, frequency_difference}` |
| `answer_non_reference_after_filter` | `vcf_path`, `exclude_intronic_intergenic` | `{total_input, non_reference, remaining}` |

---

## Common Recipes

### Recipe 1: Somatic Variant Analysis

```python
from skills.tooluniverse_variant_analysis.python_implementation import *

# Parse tumor VCF
vcf_data = parse_vcf("tumor.vcf")

# Filter for somatic-like variants
criteria = FilterCriteria(
    min_vaf=0.05,
    max_vaf=0.95,
    min_depth=20,
    pass_only=True,
    exclude_consequences=["intronic", "intergenic", "upstream", "downstream"],
    sample="TUMOR",
)
somatic, excluded = filter_variants(vcf_data.variants, criteria)

# Statistics
stats = compute_variant_statistics(somatic)
print(f"Somatic candidates: {len(somatic)}")
print(f"Missense: {stats['mutation_types'].get('missense', 0)}")
print(f"Nonsense: {stats['mutation_types'].get('nonsense', 0)}")
print(f"Frameshift: {stats['mutation_types'].get('frameshift', 0)}")
```

### Recipe 2: Clinical Variant Screening

```python
from skills.tooluniverse_variant_analysis.python_implementation import *
from tooluniverse import ToolUniverse

# Parse and annotate
vcf_data = parse_vcf("patient.vcf")
tu = ToolUniverse()
tu.load_tools()

# Annotate variants with rsIDs
rsid_variants = [v for v in vcf_data.variants if v.vid and v.vid.startswith('rs')]
annotations = batch_annotate_variants(tu, rsid_variants, max_annotate=50)

# Find clinically significant
pathogenic = [a for a in annotations
              if 'pathogenic' in (a.clinvar_classification or '').lower()]
print(f"Pathogenic variants: {len(pathogenic)}")
for a in pathogenic:
    print(f"  {a.variant_key} - {a.gene_symbol} - {a.clinvar_classification}")
```

### Recipe 3: Population Frequency Analysis

```python
from skills.tooluniverse_variant_analysis.python_implementation import *
from tooluniverse import ToolUniverse

vcf_data = parse_vcf("variants.vcf")
tu = ToolUniverse()
tu.load_tools()

annotations = batch_annotate_variants(tu, vcf_data.variants[:100])

# Rare variants (gnomAD AF < 0.01)
rare = [a for a in annotations
        if a.gnomad_af is not None and a.gnomad_af < 0.01]
print(f"Rare variants (AF < 1%): {len(rare)}")
```

### Recipe 4: DataFrame-based Analysis

```python
from skills.tooluniverse_variant_analysis.python_implementation import *

vcf_data = parse_vcf("multi_sample.vcf")
df = variants_to_dataframe(vcf_data.variants, sample="SAMPLE1")

# Group by mutation type
print(df.groupby('mutation_type').agg({'vaf': ['mean', 'count']}))

# High-impact, high-VAF variants
important = df[(df['impact'] == 'HIGH') & (df['vaf'] >= 0.3)]
print(f"\nHigh-impact, high-VAF variants: {len(important)}")
print(important[['chrom', 'pos', 'gene', 'mutation_type', 'vaf']])
```

---

## Expected Output

### Report Structure

```markdown
# Variant Analysis Report

**Generated**: 2026-02-16 10:30:00
**VCF Source**: input.vcf
**Samples**: 2 (TUMOR, NORMAL)

## 1. Summary Statistics

| Metric | Value |
|--------|-------|
| Total Variants | 1,234 |
| SNVs | 1,050 |
| Insertions | 89 |
| Deletions | 95 |
| Ti/Tv Ratio | 2.135 |

## 2. Mutation Type Distribution

| Mutation Type | Count | Percentage |
|--------------|-------|------------|
| missense | 412 | 33.39% |
| synonymous | 298 | 24.15% |
| intronic | 201 | 16.29% |
...
```

### Question Answer Format

```python
# answer_vaf_mutation_fraction returns:
{
    'total_below_vaf': 500,
    'matching_mutation_type': 125,
    'fraction': 0.25,
    'vaf_threshold': 0.3,
    'mutation_type': 'missense',
}
```

---

## Troubleshooting

### Issue: "cyvcf2 not installed"
**Solution**: `pip install cyvcf2`. The skill automatically falls back to pure Python.

### Issue: All mutation_types are "unknown"
**Solution**: VCF lacks annotation in INFO field. Either pre-annotate with SnpEff/VEP, or enable ToolUniverse annotation (`annotate=True`).

### Issue: Empty VAF values
**Solution**: VCF FORMAT does not include AF or AD. Check that your VCF caller outputs allelic depth information.

### Issue: Annotation rate limiting
**Solution**: Reduce `max_annotate` parameter. Default is 100. For large VCFs, annotate only PASS variants with rsIDs.

---

## Next Steps

After running this skill:
1. **Deep annotation**: Use `tooluniverse-variant-interpretation` for ACMG classification of specific variants
2. **Cancer context**: Use `tooluniverse-cancer-variant-interpretation` for somatic mutation clinical interpretation
3. **Population analysis**: Use gnomAD/dbSNP tools for detailed population frequency analysis
4. **Functional prediction**: Use CADD, AlphaMissense, EVE tools for pathogenicity scoring
