# VCF Filtering Reference

Complete guide to filtering variants using ToolUniverse variant analysis.

## FilterCriteria Parameters

All filter parameters are optional. Only variants matching ALL criteria are kept.

### Basic Quality Filters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `min_vaf` | float | Minimum variant allele frequency | 0.05, 0.1, 0.25 |
| `max_vaf` | float | Maximum variant allele frequency | 0.95, 0.75, 0.5 |
| `min_depth` | int | Minimum read depth (DP) | 10, 20, 30 |
| `min_qual` | float | Minimum QUAL score | 20.0, 30.0 |
| `pass_only` | bool | Only keep PASS or . (missing) FILTER | True |

### Variant Type Filters

| Parameter | Type | Description | Values |
|-----------|------|-------------|--------|
| `variant_types` | list | Include only specific variant types | ["SNV", "INS", "DEL", "MNV", "COMPLEX"] |

### Mutation Type Filters

| Parameter | Type | Description | Values |
|-----------|------|-------------|--------|
| `mutation_types` | list | Include only specific mutation types | ["missense", "nonsense", "synonymous", "frameshift", "splice_site", "splice_region", "inframe_insertion", "inframe_deletion"] |
| `exclude_consequences` | list | Exclude specific consequences | ["intronic", "intergenic", "upstream", "downstream", "UTR_5", "UTR_3"] |
| `include_consequences` | list | Include only specific consequences | ["missense", "nonsense"] |

### Genomic Region Filters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `chromosomes` | list | Include only specific chromosomes | ["1", "2", "17", "X"] |
| `min_position` | int | Minimum genomic position | 1000000 |
| `max_position` | int | Maximum genomic position | 5000000 |

### Population Frequency Filters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `max_population_freq` | float | Exclude variants above population frequency | 0.01 (1%), 0.001 (0.1%) |

### Sample-Specific Filters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `sample` | str | Apply VAF/depth filters to specific sample | "TUMOR", "NORMAL", "SAMPLE1" |

## Filter Examples

### Example 1: Somatic Variant Analysis

**Goal**: Find somatic-like variants in tumor sample

```python
from python_implementation import filter_variants, FilterCriteria

criteria = FilterCriteria(
    min_vaf=0.05,           # At least 5% allele frequency
    max_vaf=0.95,           # Not germline (not 50% or 100%)
    min_depth=20,           # Good coverage
    pass_only=True,         # Only PASS variants
    sample="TUMOR",         # Filter on tumor sample
    exclude_consequences=[  # Remove non-coding
        "intronic",
        "intergenic",
        "upstream",
        "downstream"
    ]
)

passing, failing = filter_variants(vcf_data.variants, criteria)
```

### Example 2: High-Confidence Germline

**Goal**: Find high-confidence germline variants

```python
criteria = FilterCriteria(
    min_vaf=0.25,          # At least 25% (heterozygous ~50%, homozygous ~100%)
    min_depth=30,          # High coverage
    min_qual=30.0,         # High quality
    pass_only=True,        # Only PASS
    chromosomes=[str(i) for i in range(1, 23)] + ["X", "Y"],  # Autosomes + sex chromosomes
    mutation_types=[       # High-impact mutations
        "missense",
        "nonsense",
        "frameshift",
        "splice_site"
    ]
)

passing, failing = filter_variants(vcf_data.variants, criteria)
```

### Example 3: Rare Pathogenic Candidates

**Goal**: Find rare variants likely to be pathogenic

```python
criteria = FilterCriteria(
    min_depth=20,
    pass_only=True,
    max_population_freq=0.001,  # Rare (< 0.1% in population)
    mutation_types=[            # High-impact types
        "nonsense",
        "frameshift",
        "splice_site"
    ]
)

passing, failing = filter_variants(vcf_data.variants, criteria)
```

### Example 4: Coding Variants Only

**Goal**: Remove all non-coding variants

```python
criteria = FilterCriteria(
    exclude_consequences=[
        "intronic",
        "intergenic",
        "upstream",
        "downstream",
        "UTR_5",
        "UTR_3"
    ]
)

coding, non_coding = filter_variants(vcf_data.variants, criteria)
```

### Example 5: SNVs on Specific Chromosomes

**Goal**: Analyze only SNVs on chromosomes 1, 7, 17

```python
criteria = FilterCriteria(
    variant_types=["SNV"],
    chromosomes=["1", "7", "17"]
)

passing, failing = filter_variants(vcf_data.variants, criteria)
```

### Example 6: High-VAF Missense Mutations

**Goal**: Find clonal missense mutations

```python
criteria = FilterCriteria(
    min_vaf=0.3,               # High VAF (clonal)
    mutation_types=["missense"]
)

passing, failing = filter_variants(vcf_data.variants, criteria)
```

## Specialized Filters

### Filter Non-Reference Variants

Remove variants where all samples are 0/0 (homozygous reference):

```python
from python_implementation import filter_non_reference_variants

non_ref, ref_only = filter_non_reference_variants(vcf_data.variants)
```

### Filter Intronic/Intergenic Variants

Remove purely intronic, intergenic, upstream, and downstream variants (keeps splice_region):

```python
from python_implementation import filter_intronic_intergenic

coding, non_coding = filter_intronic_intergenic(vcf_data.variants)
```

## Combining Filters

Filters can be combined. All criteria must be met:

```python
# High-quality somatic coding variants
criteria = FilterCriteria(
    min_vaf=0.1,
    max_vaf=0.9,
    min_depth=30,
    pass_only=True,
    sample="TUMOR",
    exclude_consequences=["intronic", "intergenic", "upstream", "downstream"],
    mutation_types=["missense", "nonsense", "frameshift", "splice_site"]
)
```

## VAF Extraction Methods

When filtering by VAF, the skill tries these methods in order:

1. **AF/VAF/FREQ format field**: Direct allele frequency
2. **AD (allelic depth)**: `alt_depth / (ref_depth + alt_depth)`
3. **AO/RO (FreeBayes)**: `alt_obs / (alt_obs + ref_obs)`
4. **NR/NV**: `variant_reads / total_reads`
5. **INFO AF field**: Fallback for all samples

If no VAF can be extracted, VAF filters are not applied to that variant.

## Multi-Sample VCFs

For multi-sample VCFs, specify which sample to filter on:

```python
criteria = FilterCriteria(
    min_vaf=0.1,
    min_depth=20,
    sample="TUMOR"  # Apply filters to TUMOR sample only
)
```

If `sample` is not specified:
- VAF/depth filters are applied to the first sample
- Other filters (quality, type) apply to all variants

## Filter Statistics

After filtering, you can compute statistics on both passing and failing sets:

```python
from python_implementation import compute_variant_statistics

passing, failing = filter_variants(vcf_data.variants, criteria)

stats_passing = compute_variant_statistics(passing)
stats_failing = compute_variant_statistics(failing)

print(f"Passing: {len(passing)} variants")
print(f"Failing: {len(failing)} variants")
print(f"Ti/Tv (passing): {stats_passing['ti_tv_ratio']}")
```

## Performance Tips

1. **Parse with cyvcf2 for large VCFs**: Much faster than pure Python
2. **Filter early**: Apply filters during parsing if possible
3. **Use specific filters**: More specific filters = faster processing
4. **Avoid population frequency filters**: Requires annotation (slower)

## Common Filter Combinations

### Cancer Somatic Variants
```python
FilterCriteria(
    min_vaf=0.05, max_vaf=0.95,
    min_depth=20, pass_only=True,
    sample="TUMOR",
    exclude_consequences=["intronic", "intergenic", "upstream", "downstream"]
)
```

### Rare Germline Pathogenic
```python
FilterCriteria(
    min_depth=20, pass_only=True,
    max_population_freq=0.01,
    mutation_types=["missense", "nonsense", "frameshift", "splice_site"]
)
```

### High-Confidence Coding
```python
FilterCriteria(
    min_depth=30, min_qual=30.0, pass_only=True,
    exclude_consequences=["intronic", "intergenic", "upstream", "downstream", "UTR_5", "UTR_3"]
)
```

### Loss-of-Function
```python
FilterCriteria(
    min_depth=20, pass_only=True,
    mutation_types=["nonsense", "frameshift", "splice_site"]
)
```
