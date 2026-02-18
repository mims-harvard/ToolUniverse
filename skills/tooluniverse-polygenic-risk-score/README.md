# Polygenic Risk Score (PRS) Builder

**A ToolUniverse skill for building and interpreting polygenic risk scores for complex diseases.**

---

## Quick Links

- **[QUICK_START.md](QUICK_START.md)** - Get started in 5 minutes with practical examples
- **[SKILL.md](SKILL.md)** - Comprehensive methodology, theory, and best practices
- **[python_implementation.py](python_implementation.py)** - Reference implementation with demo
- **[SKILL_SUMMARY.md](SKILL_SUMMARY.md)** - Architecture and technical overview

---

## What is This?

Build polygenic risk scores using GWAS data to estimate genetic predisposition to diseases:

```python
from tooluniverse_polygenic_risk_score import (
    build_polygenic_risk_score,
    calculate_personal_prs,
    interpret_prs_percentile
)

# Build PRS for type 2 diabetes
prs = build_polygenic_risk_score("type 2 diabetes")

# Calculate your personal risk from genotypes
result = calculate_personal_prs(prs, my_genotypes)
result = interpret_prs_percentile(result)

print(f"Percentile: {result.percentile:.1f}%")
print(f"Risk: {result.risk_category}")
```

---

## Features

✅ **Automatic GWAS Query** - Extracts genome-wide significant variants (p < 5×10⁻⁸)
✅ **Effect Size Handling** - Supports beta coefficients and odds ratios
✅ **Personal Risk Calculation** - Computes PRS from 23andMe/Ancestry/WGS data
✅ **Percentile Interpretation** - Population-based risk categories
✅ **No API Keys Required** - All GWAS tools are public
✅ **Thoroughly Tested** - 12/12 tests passing (100%)
✅ **Well Documented** - Methodology, ethics, limitations, and references

---

## Installation

```bash
pip install tooluniverse
```

No additional dependencies required.

---

## Use Cases

### Clinical Risk Assessment
- Screen high-risk individuals for prevention programs
- Personalize intervention strategies based on genetic risk
- Combine PRS with clinical risk factors (family history, lifestyle)

### Research Applications
- Gene discovery via PRS-based phenome-wide studies
- Genetic correlation analyses across traits
- Mendelian randomization using PRS as instruments

### Personal Genomics
- Calculate PRS for traits not reported by consumer testing
- Understand genetic contribution vs. environmental factors
- Compare to population distributions

---

## Supported Traits

Works with any trait in GWAS Catalog. Well-validated traits include:

- **Cardiovascular**: Coronary artery disease, hypertension, atrial fibrillation
- **Metabolic**: Type 2 diabetes, obesity, hyperlipidemia
- **Neurodegenerative**: Alzheimer's disease, Parkinson's disease
- **Psychiatric**: Schizophrenia, bipolar disorder, major depression
- **Cancer**: Breast cancer, prostate cancer, colorectal cancer
- **Autoimmune**: Rheumatoid arthritis, inflammatory bowel disease, type 1 diabetes

---

## Example: Type 2 Diabetes PRS

```python
# Step 1: Build PRS model from GWAS data
prs = build_polygenic_risk_score(
    trait="type 2 diabetes",
    p_threshold=5e-8,  # Genome-wide significance
    max_snps=100
)

print(f"Built PRS with {prs.snp_count} genome-wide significant SNPs")

# View top risk variants
for i, snp in enumerate(prs.snp_weights[:5], 1):
    print(f"{i}. {snp.rs_id} ({snp.gene}): beta={snp.effect_size:.3f}")

# Output:
# Built PRS with 42 genome-wide significant SNPs
# 1. rs7903146 (TCF7L2): beta=0.389
# 2. rs10811661 (CDKN2A/B): beta=0.194
# 3. rs5219 (KCNJ11): beta=0.156
# 4. rs1801282 (PPARG): beta=-0.145
# 5. rs7756992 (CDKAL1): beta=0.125
```

```python
# Step 2: Calculate your personal PRS
my_genotypes = {
    "rs7903146": ("C", "T"),  # Heterozygous for risk allele
    "rs10811661": ("T", "T"),  # Homozygous for risk allele
    # ... add more SNPs from your 23andMe/Ancestry data
}

result = calculate_personal_prs(prs, my_genotypes)
result = interpret_prs_percentile(result)

# Output:
# PRS: 0.683
# Percentile: 75.2%
# Risk category: Average risk
```

---

## Documentation

### For Users

- **[QUICK_START.md](QUICK_START.md)** - Installation, basic usage, examples, troubleshooting
  - Build PRS models
  - Calculate personal risk
  - Work with genotype data (23andMe, VCF, etc.)
  - Advanced usage and integrations

### For Researchers

- **[SKILL.md](SKILL.md)** - Complete scientific documentation
  - PRS methodology and formulas
  - GWAS concepts (effect sizes, LD, population structure)
  - Applications (clinical, research, personal genomics)
  - Limitations and ethical considerations
  - References to key publications
  - Best practices

### For Developers

- **[python_implementation.py](python_implementation.py)** - Reference implementation
  - Fully commented code
  - Type hints and dataclasses
  - Runnable demo mode
  - Production considerations

- **[SKILL_SUMMARY.md](SKILL_SUMMARY.md)** - Technical overview
  - Architecture and components
  - Tools used
  - Testing strategy
  - Integration examples

---

## Testing

Comprehensive test suite: `test_skill_comprehensive.py`

**Results: 12/12 tests passing (100%)**

```bash
python test_skill_comprehensive.py
```

Tests cover:
- PRS building for multiple traits (CAD, T2D, Alzheimer's)
- Personal PRS calculation from genotypes
- Percentile interpretation and risk categories
- Documentation examples validation
- Edge cases and error handling
- Data structure validation
- OR vs Beta conversion
- Full workflow integration

See [SKILL_TESTING_REPORT.md](SKILL_TESTING_REPORT.md) for detailed results.

---

## Tools Used

From ToolUniverse (no API keys required):

- `gwas_get_associations_for_trait` - Query GWAS Catalog by disease/trait
- `gwas_get_snp_by_id` - Lookup SNP details (rs ID, position, alleles)
- `gwas_get_associations_for_snp` - Find all trait associations for SNP
- `gwas_get_study_by_id` - Get GWAS study metadata
- `OpenTargets_search_gwas_studies_by_disease` - Search by disease ontology
- `OpenTargets_get_variant_info` - Get variant annotations and frequencies

---

## Working with Genotype Data

### From 23andMe

```python
def parse_23andme(file_path):
    genotypes = {}
    with open(file_path) as f:
        for line in f:
            if line.startswith('#'):
                continue
            parts = line.strip().split('\t')
            if len(parts) >= 4:
                rsid = parts[0]
                genotype = parts[3]
                if len(genotype) == 2:
                    genotypes[rsid] = (genotype[0], genotype[1])
    return genotypes

my_genotypes = parse_23andme("my_raw_data.txt")
```

### From VCF Files

```python
import vcf

def parse_vcf(file_path, sample_name):
    genotypes = {}
    vcf_reader = vcf.Reader(filename=file_path)
    for record in vcf_reader:
        if record.ID:
            sample = record.genotype(sample_name)
            gt = sample.gt_alleles
            if gt and len(gt) == 2:
                genotypes[record.ID[0]] = (gt[0], gt[1])
    return genotypes

my_genotypes = parse_vcf("my_genome.vcf.gz", "individual_001")
```

---

## Limitations & Disclaimers

### Scientific Limitations
- PRS explains only a fraction of genetic heritability (10-20% for most traits)
- Most GWAS are European ancestry - accuracy lower in other populations
- Does not account for rare variants, epistasis, or gene-environment interactions
- Effect sizes from discovery cohorts may be overestimated (winner's curse)

### Clinical Limitations
- **NOT DIAGNOSTIC** - PRS is probabilistic, not deterministic
- **NOT VALIDATED FOR CLINICAL USE** - Educational/research tool only
- High PRS ≠ guaranteed disease; Low PRS ≠ guaranteed protection
- Many diseases are 50%+ environmental (lifestyle, diet, stress)

### Ethical Considerations
- Genetic data is identifiable and permanent
- Potential for discrimination (insurance, employment)
- Psychological impact of knowing genetic risk
- Ancestry bias creates health equity concerns

### Recommendations
- **For clinical use**: Consult genetic counselors and use validated PRS from [PGS Catalog](https://www.pgscatalog.org/)
- **For research**: Validate in held-out cohorts and test across ancestries
- **For personal use**: Combine with family history and clinical risk factors

---

## References

### Key Publications

1. **Lambert et al. (2021)**: "The Polygenic Score Catalog" - Repository of validated PRS models
2. **Khera et al. (2018)**: "Genome-wide polygenic scores for common diseases" - Demonstrated clinical utility
3. **Torkamani et al. (2018)**: "The personal and clinical utility of polygenic risk scores" - Comprehensive review
4. **Martin et al. (2019)**: "Clinical use may exacerbate health disparities" - Addresses equity concerns
5. **Choi et al. (2020)**: "Tutorial: a guide to performing PRS analyses" - Practical guide

### Resources

- **PGS Catalog**: https://www.pgscatalog.org/ - Published PRS models
- **GWAS Catalog**: https://www.ebi.ac.uk/gwas/ - Association database
- **PRSice**: https://www.prsice.info/ - PRS calculation software
- **LD Hub**: http://ldsc.broadinstitute.org/ - Genetic correlations

---

## Production Considerations

This skill provides a research/educational implementation. Production systems should additionally include:

- **LD clumping**: Remove correlated SNPs (use PLINK, PRSice)
- **Ancestry matching**: Train and apply PRS in same population
- **Validation cohorts**: Test performance on held-out data
- **Updated GWAS**: Use latest meta-analyses and fine-mapping
- **Clinical validation**: Regulatory approval for clinical use

**For clinical-grade PRS, use validated models from PGS Catalog.**

---

## Integration

### With MCP (Model Context Protocol)

```python
from fastmcp import FastMCP

mcp = FastMCP("PRS Builder")

@mcp.tool()
def build_prs(trait: str) -> dict:
    from tooluniverse_polygenic_risk_score import build_polygenic_risk_score
    result = build_polygenic_risk_score(trait)
    return {"trait": result.trait, "snp_count": result.snp_count}

@mcp.tool()
def calculate_prs(trait: str, genotypes: dict) -> dict:
    from tooluniverse_polygenic_risk_score import (
        build_polygenic_risk_score,
        calculate_personal_prs,
        interpret_prs_percentile
    )
    prs_model = build_polygenic_risk_score(trait)
    result = calculate_personal_prs(prs_model, genotypes)
    result = interpret_prs_percentile(result)
    return {
        "prs_value": result.prs_value,
        "percentile": result.percentile,
        "risk_category": result.risk_category
    }
```

### With ToolUniverse SDK

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

# Use GWAS tools directly
associations = tu.tools.gwas_get_associations_for_trait(
    disease_trait="coronary artery disease",
    size=100
)
```

---

## Contributing

To improve this skill:

1. **Bug fixes**: Submit issues on GitHub
2. **New features**: Propose enhancements (LD clumping, multi-ancestry, etc.)
3. **Documentation**: Clarify methodology or add examples
4. **Validation**: Test on new traits and report results

---

## License

Part of ToolUniverse. See main repository for license details.

---

## Support

- **Documentation**: See SKILL.md for comprehensive guide
- **Testing**: Run test_skill_comprehensive.py
- **Questions**: Open GitHub issue
- **Clinical interpretation**: Consult certified genetic counselor

---

## Status

✅ **Complete and validated**
📊 **12/12 tests passing (100%)**
📚 **Comprehensive documentation**
🔬 **Research-ready**
⚠️ **Educational use only - not for clinical diagnosis**

---

**Created**: 2026-02-13
**Version**: 1.0
**Language**: Python 3.8+
**Dependencies**: ToolUniverse only

