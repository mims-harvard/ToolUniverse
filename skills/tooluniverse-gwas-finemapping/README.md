# GWAS Fine-Mapping & Causal Variant Prioritization

> Identify and prioritize causal variants at GWAS loci using statistical fine-mapping and locus-to-gene predictions.

## Overview

This ToolUniverse skill enables systematic identification of causal variants from GWAS data using:
- **Statistical fine-mapping** (SuSiE, FINEMAP, etc.) to compute posterior probabilities
- **Locus-to-gene (L2G) predictions** to link variants to their likely causal genes
- **Functional annotations** from GWAS Catalog and Open Targets Genetics
- **Integration** of multiple data sources for comprehensive variant prioritization

## Quick Start

```python
from python_implementation import prioritize_causal_variants

# Prioritize variants in TCF7L2 for diabetes
result = prioritize_causal_variants("TCF7L2", "type 2 diabetes")
print(result.get_summary())

# Output:
# Query Gene: TCF7L2
# Credible Sets Found: 8
# Top Causal Genes:
#   - TCF7L2 (L2G score: 0.863)
```

## Documentation

- **[SKILL.md](./SKILL.md)**: Complete skill documentation with concepts, workflows, and examples
- **[QUICK_START.md](./QUICK_START.md)**: 5-minute getting started guide
- **[SKILL_TESTING_REPORT.md](./SKILL_TESTING_REPORT.md)**: Comprehensive testing results (100% pass rate)

## Key Features

### 1. Variant Prioritization
Rank variants by posterior probability of being causal:
```python
result = prioritize_causal_variants("APOE", "alzheimer")
for cs in result.credible_sets:
    print(f"{cs.trait}: {cs.lead_variant.rs_ids[0]}")
    print(f"  Method: {cs.finemapping_method}")
    print(f"  Top gene: {cs.l2g_genes[0]}")
```

### 2. Study Exploration
Get all fine-mapped loci from a GWAS:
```python
from python_implementation import get_credible_sets_for_study

credible_sets = get_credible_sets_for_study("GCST90029024")
print(f"Found {len(credible_sets)} independent loci")
```

### 3. Disease Study Search
Find relevant GWAS studies:
```python
from python_implementation import search_gwas_studies_for_disease

studies = search_gwas_studies_for_disease("type 2 diabetes", "MONDO_0005148")
for study in studies:
    print(f"{study['id']}: {study.get('nSamples', 'N/A')} samples")
```

### 4. Validation Planning
Get experimental validation suggestions:
```python
suggestions = result.get_validation_suggestions()
# Suggests: CRISPR assays, eQTL analysis, colocalization, replication
```

## Use Cases

1. **Locus Prioritization**: "Which variant at this locus is causal?"
2. **Gene Discovery**: "Which genes does this variant affect?"
3. **Study Exploration**: "What are all the T2D risk loci?"
4. **Validation Planning**: "How should we experimentally validate this?"
5. **Meta-Analysis**: "Compare fine-mapping across multiple studies"

## Testing Status

✓ **100% Test Pass Rate** (10/10 comprehensive tests)

Tested with real-world examples:
- **APOE** and Alzheimer's disease
- **TCF7L2** and type 2 diabetes
- **FTO** and obesity

See [SKILL_TESTING_REPORT.md](./SKILL_TESTING_REPORT.md) for details.

## Tools Used

### Open Targets Genetics (GraphQL)
- Get variant info and credible sets
- Study-level credible set queries
- Disease-based study search
- L2G predictions

### GWAS Catalog (REST)
- SNP search by gene/rsID
- Association queries
- Study metadata

No API keys required - all data is public.

## Installation

```bash
pip install tooluniverse
```

## Files

- `python_implementation.py`: Main Python SDK implementation
- `SKILL.md`: Complete documentation
- `QUICK_START.md`: Quick reference
- `test_skill_comprehensive.py`: Test suite (10 tests)
- `SKILL_TESTING_REPORT.md`: Testing report
- `README.md`: This file

## Requirements

- Python 3.8+
- ToolUniverse >= 1.0.0
- No API keys needed

## Examples

### Example 1: Complete Fine-Mapping Workflow

```python
from python_implementation import (
    search_gwas_studies_for_disease,
    get_credible_sets_for_study,
    prioritize_causal_variants
)

# Step 1: Find T2D studies
studies = search_gwas_studies_for_disease("type 2 diabetes", "MONDO_0005148")
largest = max(studies, key=lambda s: s.get('nSamples', 0) or 0)

# Step 2: Get all loci
credible_sets = get_credible_sets_for_study(largest['id'])

# Step 3: Prioritize TCF7L2 variants
result = prioritize_causal_variants("TCF7L2", "type 2 diabetes")

# Step 4: Generate report
print(result.get_summary())
for suggestion in result.get_validation_suggestions():
    print(suggestion)
```

### Example 2: Variant-Centric Analysis

```python
# Start with a known variant
result = prioritize_causal_variants("rs429358")  # APOE4

# Check all traits
print(f"Associated with {len(set(result.associated_traits))} traits")

# Find credible sets
for cs in result.credible_sets:
    print(f"{cs.trait}: {cs.l2g_genes[0] if cs.l2g_genes else 'No gene'}")
```

## Key Concepts

### Credible Sets
A minimal set of variants containing the causal variant with 95-99% probability. Each variant has a posterior probability of causality.

### Posterior Probability
The probability that a specific variant is causal, given GWAS data and LD structure. Higher values indicate stronger candidates.

### L2G Score
Locus-to-gene score (0-1) integrating distance, eQTLs, chromatin interactions, and functional annotations. Higher scores = stronger gene-variant links.

### Fine-Mapping Methods
- **SuSiE**: Handles multiple causal variants per locus
- **FINEMAP**: Fast Bayesian stochastic search
- **PAINTOR**: Integrates functional annotations

## Biological Validation

Results validated against known biology:
- **rs429358** (APOE4) → High L2G for APOE, Alzheimer's association ✓
- **rs7903146** (TCF7L2) → Strong diabetes association, TCF7L2 top gene ✓
- **rs9939609** (FTO) → BMI/obesity traits, intergenic variant ✓

## Contributing

This skill follows the ToolUniverse skill creation workflow:
1. Domain analysis
2. Tool testing
3. Implementation
4. Documentation
5. Comprehensive testing

## License

MIT License - see ToolUniverse main repository

## Citation

If you use this skill, please cite:
- **Open Targets Genetics**: Ghoussaini et al. (2021) Nature Genetics
- **GWAS Catalog**: Sollis et al. (2023) Nucleic Acids Research
- **SuSiE**: Wang et al. (2020) JRSS-B
- **L2G method**: Mountjoy et al. (2021) Nature Genetics

## Support

- Documentation: See [SKILL.md](./SKILL.md)
- Issues: Create GitHub issue in ToolUniverse repository
- Questions: Check [QUICK_START.md](./QUICK_START.md)

## Changelog

### v1.0.0 (2026-02-13)
- Initial release
- 10 comprehensive tests (100% pass rate)
- Support for gene and variant queries
- Study-level analysis
- Validation suggestions
- Complete documentation
