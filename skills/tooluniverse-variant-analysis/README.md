# tooluniverse-variant-analysis

Production-ready VCF processing, variant annotation, and mutation analysis for bioinformatics.

## Overview

This skill provides comprehensive variant analysis capabilities:

- **VCF Parsing**: Pure Python + cyvcf2 parsers supporting VCF 4.x, gzipped, multi-sample files
- **Mutation Classification**: Automatic mapping of SnpEff, VEP, and GATK annotations to standardized mutation types
- **Flexible Filtering**: VAF, depth, quality, consequence, population frequency, chromosome
- **ToolUniverse Integration**: Annotation via MyVariant.info (ClinVar, dbSNP, gnomAD, CADD, SIFT, PolyPhen)
- **BixBench Support**: Designed to answer bioinformatics analysis questions about VCF data

## Installation

```bash
# Required
pip install pandas

# Recommended (faster VCF parsing)
pip install cyvcf2 pysam

# For ToolUniverse annotation
pip install tooluniverse
```

## Quick Start

```python
from python_implementation import (
    parse_vcf,
    filter_variants,
    compute_variant_statistics,
    answer_vaf_mutation_fraction,
    FilterCriteria,
)

# Parse VCF
vcf_data = parse_vcf("variants.vcf")
print(f"Variants: {len(vcf_data.variants)}, Samples: {vcf_data.samples}")

# Filter
criteria = FilterCriteria(min_vaf=0.1, min_depth=20, pass_only=True)
passing, failing = filter_variants(vcf_data.variants, criteria)

# Statistics
stats = compute_variant_statistics(passing)
print(f"Ti/Tv: {stats['ti_tv_ratio']}")
print(f"Missense: {stats['mutation_types'].get('missense', 0)}")

# Answer BixBench question
result = answer_vaf_mutation_fraction("variants.vcf", max_vaf=0.3, mutation_type="missense")
print(f"Fraction of VAF<0.3 that are missense: {result['fraction']:.4f}")
```

## Files

| File | Description |
|------|-------------|
| `python_implementation.py` | Core implementation (parsing, filtering, annotation, reporting) |
| `test_variant_analysis.py` | Comprehensive test suite (58 tests) |
| `SKILL.md` | Detailed skill documentation |
| `QUICK_START.md` | Usage examples for Python SDK and MCP |
| `README.md` | This file |
| `test_data/sample.vcf` | Test VCF (24 variants, 2 samples, annotated) |
| `test_data/cohort2.vcf` | Second test VCF for cohort comparison |

## Test Results

```
58/58 tests passed (100%)

Phase 1: VCF Parsing         - 10/10 PASS
Phase 2: Classification       - 10/10 PASS
Phase 3: Filtering            - 12/12 PASS
Phase 4: Statistics           -  4/4  PASS
Phase 5: BixBench Questions   - 10/10 PASS
Phase 6: DataFrame            -  3/3  PASS
Phase 7: Report Generation    -  2/2  PASS
Phase 8: ToolUniverse Annot.  -  3/3  PASS
Phase 9: Edge Cases           -  4/4  PASS
```

## Key Capabilities

### Mutation Types Supported

| Type | Examples |
|------|---------|
| missense | p.V600E, p.L858R |
| nonsense | p.R273* |
| synonymous | p.Ala67= |
| frameshift | p.Val234Glyfs*6 |
| splice_site | splice_acceptor_variant |
| splice_region | splice_region_variant |
| inframe_insertion | p.insAla |
| inframe_deletion | p.Arg194del |
| intronic | intron_variant |
| intergenic | intergenic_variant |
| UTR_5 / UTR_3 | 5'/3' UTR variants |

### VAF Extraction Formats

| Format | Field | Computation |
|--------|-------|------------|
| Direct AF | FORMAT:AF | Use directly |
| Allelic Depth | FORMAT:AD | alt / (ref + alt) |
| FreeBayes | FORMAT:AO/RO | AO / (AO + RO) |
| NR/NV | FORMAT:NR/NV | NV / NR |
| INFO AF | INFO:AF | Fallback for all samples |

### ToolUniverse Annotation Sources

| Source | Data | Via |
|--------|------|-----|
| ClinVar | Clinical significance | MyVariant.info |
| dbSNP | rsID, population frequencies | MyVariant.info or direct |
| gnomAD | Allele frequencies (global + ancestry) | MyVariant.info or direct |
| CADD | Deleteriousness score (PHRED) | MyVariant.info |
| SIFT | Functional prediction | MyVariant.info (CADD) |
| PolyPhen | Functional prediction | MyVariant.info (CADD) |

## Running Tests

```bash
python test_variant_analysis.py
```

## Command Line Usage

```bash
python python_implementation.py variants.vcf -o report.md --annotate --min-vaf 0.1 --pass-only
```

## License

Part of the ToolUniverse project.
