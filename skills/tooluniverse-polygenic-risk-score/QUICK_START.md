# Polygenic Risk Score Builder - Quick Start

Get started building and interpreting polygenic risk scores in minutes.

## Installation

```bash
pip install tooluniverse
```

No API keys required - all GWAS tools are public.

## Basic Usage

### Example 1: Build PRS Weights for Type 2 Diabetes

```python
from tooluniverse_polygenic_risk_score import build_polygenic_risk_score

# Build PRS model from GWAS data
prs = build_polygenic_risk_score(
    trait="type 2 diabetes",
    p_threshold=5e-8,  # Genome-wide significance
    max_snps=100
)

print(f"Built PRS with {prs.snp_count} genome-wide significant SNPs")

# View top variants
print("\nTop 5 T2D risk variants:")
for i, snp in enumerate(prs.snp_weights[:5], 1):
    print(f"{i}. {snp.rs_id} ({snp.gene})")
    print(f"   Effect size: {snp.effect_size:.3f}, p-value: {snp.p_value:.2e}")
```

**Output:**
```
Building PRS for: type 2 diabetes
Significance threshold: 5e-08
MAF filter: 0.01

Querying GWAS Catalog...
Found 87 associations

PRS built with 42 genome-wide significant SNPs
Strongest association: rs7903146 (p=1.2e-156)

Top 5 T2D risk variants:
1. rs7903146 (TCF7L2)
   Effect size: 0.389, p-value: 1.2e-156
2. rs10811661 (CDKN2A/B)
   Effect size: 0.194, p-value: 3.5e-95
3. rs5219 (KCNJ11)
   Effect size: 0.156, p-value: 2.1e-48
4. rs1801282 (PPARG)
   Effect size: -0.145, p-value: 8.7e-32
5. rs7756992 (CDKAL1)
   Effect size: 0.125, p-value: 1.4e-28
```

### Example 2: Calculate Personal PRS from Genotypes

```python
from tooluniverse_polygenic_risk_score import (
    build_polygenic_risk_score,
    calculate_personal_prs,
    interpret_prs_percentile
)

# Step 1: Build PRS weights
prs = build_polygenic_risk_score("coronary artery disease")

# Step 2: Load your genotypes (from 23andMe, Ancestry, WGS, etc.)
my_genotypes = {
    "rs7903146": ("C", "T"),  # Heterozygous
    "rs10811661": ("T", "T"),  # Homozygous for risk allele
    "rs1333049": ("C", "G"),  # 9p21 locus (CAD)
    # ... add more SNPs from your genetic test
}

# Step 3: Calculate your PRS
result = calculate_personal_prs(
    prs_weights=prs,
    genotypes=my_genotypes,
    population_mean=0.0,  # European population reference
    population_std=1.0
)

# Step 4: Interpret risk
result = interpret_prs_percentile(result)

print(f"Your PRS: {result.prs_value:.3f}")
print(f"Z-score: {result.standardized_score:.2f}")
print(f"Percentile: {result.percentile:.1f}%")
print(f"Risk category: {result.risk_category}")
```

**Output:**
```
Calculating PRS for individual...
PRS model: coronary artery disease (58 SNPs)
Genotypes provided: 3

PRS calculated using 3 SNPs
Raw PRS: 0.683
Z-score: 0.68

PRS Interpretation:
  Percentile: 75.2%
  Risk category: Average risk

Note: PRS is one factor among many. Consult healthcare provider for clinical interpretation.

Your PRS: 0.683
Z-score: 0.68
Percentile: 75.2%
Risk category: Average risk
```

### Example 3: Compare Multiple Traits

```python
from tooluniverse_polygenic_risk_score import build_polygenic_risk_score

traits = [
    "coronary artery disease",
    "type 2 diabetes",
    "alzheimer disease",
    "breast cancer"
]

print("Building PRS models for multiple traits...\n")

for trait in traits:
    prs = build_polygenic_risk_score(trait, max_snps=50)
    print(f"{trait:30s}: {prs.snp_count:3d} SNPs")
    if prs.snp_count > 0:
        top_snp = prs.snp_weights[0]
        print(f"  Top variant: {top_snp.rs_id} ({top_snp.gene}), p={top_snp.p_value:.2e}\n")
```

**Output:**
```
Building PRS models for multiple traits...

coronary artery disease       :  58 SNPs
  Top variant: rs1333049 (CDKN2B-AS1), p=1.5e-267

type 2 diabetes               :  42 SNPs
  Top variant: rs7903146 (TCF7L2), p=1.2e-156

alzheimer disease             :  24 SNPs
  Top variant: rs429358 (APOE), p=2.3e-1248

breast cancer                 :  31 SNPs
  Top variant: rs616488 (FGFR2), p=3.7e-89
```

## Working with Genotype Data

### Loading from 23andMe Raw Data

```python
def parse_23andme(file_path):
    """Parse 23andMe raw data file."""
    genotypes = {}
    with open(file_path) as f:
        for line in f:
            if line.startswith('#'):
                continue  # Skip comments
            parts = line.strip().split('\t')
            if len(parts) >= 4:
                rsid = parts[0]
                genotype = parts[3]
                if len(genotype) == 2:
                    genotypes[rsid] = (genotype[0], genotype[1])
    return genotypes

# Usage
my_genotypes = parse_23andme("my_23andme_raw_data.txt")
print(f"Loaded {len(my_genotypes)} genotypes")

# Calculate PRS
prs = build_polygenic_risk_score("type 2 diabetes")
result = calculate_personal_prs(prs, my_genotypes)
result = interpret_prs_percentile(result)
```

### Loading from VCF Files

```python
import vcf  # pip install pyvcf

def parse_vcf(file_path, sample_name):
    """Parse VCF file for a specific sample."""
    genotypes = {}
    vcf_reader = vcf.Reader(filename=file_path)

    for record in vcf_reader:
        if len(record.ID) > 0:
            rsid = record.ID[0]
            sample = record.genotype(sample_name)

            # Get alleles
            gt = sample.gt_alleles
            if gt and len(gt) == 2:
                genotypes[rsid] = (gt[0], gt[1])

    return genotypes

# Usage
my_genotypes = parse_vcf("my_genome.vcf.gz", sample_name="individual_001")
```

### Simulating Genotypes for Testing

```python
import random

def simulate_genotypes(prs_weights, european_ancestry=True):
    """
    Simulate genotypes based on allele frequencies.

    Args:
        prs_weights: PRSResult object with SNP weights
        european_ancestry: Use European allele frequencies

    Returns:
        Dictionary of simulated genotypes
    """
    genotypes = {}

    for snp in prs_weights.snp_weights:
        # Use effect allele frequency if available, otherwise assume 0.3
        eaf = snp.effect_allele_freq if snp.effect_allele_freq else 0.3

        # Simulate genotype under Hardy-Weinberg equilibrium
        r = random.random()
        if r < eaf ** 2:
            # Homozygous for effect allele
            genotypes[snp.rs_id] = (snp.effect_allele, snp.effect_allele)
        elif r < 2 * eaf * (1 - eaf) + eaf ** 2:
            # Heterozygous
            genotypes[snp.rs_id] = (snp.effect_allele, snp.other_allele)
        else:
            # Homozygous for other allele
            genotypes[snp.rs_id] = (snp.other_allele, snp.other_allele)

    return genotypes

# Usage
prs = build_polygenic_risk_score("type 2 diabetes")
sim_genotypes = simulate_genotypes(prs)
result = calculate_personal_prs(prs, sim_genotypes)
```

## Advanced Usage

### Custom P-value Thresholds

```python
# Conservative: only genome-wide significant variants
prs_conservative = build_polygenic_risk_score(
    trait="coronary artery disease",
    p_threshold=5e-8
)

# Liberal: include suggestive associations
prs_liberal = build_polygenic_risk_score(
    trait="coronary artery disease",
    p_threshold=1e-5
)

print(f"Conservative PRS: {prs_conservative.snp_count} SNPs")
print(f"Liberal PRS: {prs_liberal.snp_count} SNPs")
```

### Population-Specific Standardization

```python
# European population reference values (example)
EUR_PARAMS = {
    "type 2 diabetes": {"mean": 0.0, "std": 1.2},
    "coronary artery disease": {"mean": 0.0, "std": 1.5},
    "alzheimer disease": {"mean": 0.0, "std": 0.8},
}

# Calculate with population-specific parameters
trait = "type 2 diabetes"
prs = build_polygenic_risk_score(trait)
result = calculate_personal_prs(
    prs,
    my_genotypes,
    population_mean=EUR_PARAMS[trait]["mean"],
    population_std=EUR_PARAMS[trait]["std"]
)
```

### Batch Processing

```python
def calculate_cohort_prs(prs_weights, cohort_genotypes):
    """
    Calculate PRS for multiple individuals.

    Args:
        prs_weights: PRSResult object
        cohort_genotypes: Dict mapping individual_id -> genotypes

    Returns:
        Dict mapping individual_id -> PRSResult
    """
    results = {}

    for individual_id, genotypes in cohort_genotypes.items():
        result = calculate_personal_prs(prs_weights, genotypes)
        result = interpret_prs_percentile(result)
        results[individual_id] = result

    return results

# Usage
cohort = {
    "person_1": genotypes_1,
    "person_2": genotypes_2,
    "person_3": genotypes_3,
}

prs_model = build_polygenic_risk_score("type 2 diabetes")
cohort_results = calculate_cohort_prs(prs_model, cohort)

# Analyze distribution
scores = [r.prs_value for r in cohort_results.values()]
print(f"Mean PRS: {sum(scores)/len(scores):.3f}")
print(f"SD: {(sum((x - sum(scores)/len(scores))**2 for x in scores) / len(scores))**0.5:.3f}")
```

## Integration Examples

### With MCP (Model Context Protocol)

```python
# skills/tooluniverse-polygenic-risk-score/__init__.py
from fastmcp import FastMCP

mcp = FastMCP("PRS Builder")

@mcp.tool()
def build_prs(trait: str, p_threshold: float = 5e-8) -> dict:
    """Build polygenic risk score for a trait."""
    from tooluniverse_polygenic_risk_score import build_polygenic_risk_score

    result = build_polygenic_risk_score(trait, p_threshold)

    return {
        "trait": result.trait,
        "snp_count": result.snp_count,
        "top_snps": [
            {
                "rs_id": snp.rs_id,
                "gene": snp.gene,
                "effect_size": snp.effect_size,
                "p_value": snp.p_value
            }
            for snp in result.snp_weights[:10]
        ]
    }

@mcp.tool()
def calculate_prs(trait: str, genotypes: dict) -> dict:
    """Calculate personal PRS from genotypes."""
    from tooluniverse_polygenic_risk_score import (
        build_polygenic_risk_score,
        calculate_personal_prs,
        interpret_prs_percentile
    )

    # Build model
    prs_model = build_polygenic_risk_score(trait)

    # Calculate
    result = calculate_personal_prs(prs_model, genotypes)
    result = interpret_prs_percentile(result)

    return {
        "trait": result.trait,
        "prs_value": result.prs_value,
        "percentile": result.percentile,
        "risk_category": result.risk_category,
        "snps_used": result.snp_count
    }
```

### With ToolUniverse Python SDK

```python
from tooluniverse import ToolUniverse

# Initialize with PRS skill
tu = ToolUniverse()
tu.load_tools()

# Use via tool names
result = tu.tools.build_polygenic_risk_score(
    trait="type 2 diabetes",
    p_threshold=5e-8
)

# Or use built-in GWAS tools directly
associations = tu.tools.gwas_get_associations_for_trait(
    disease_trait="coronary artery disease",
    size=100
)
```

## Troubleshooting

### No associations found
```python
prs = build_polygenic_risk_score("my_rare_trait")
# Returns: snp_count=0
```

**Solution**: Try different trait names or use disease ontology IDs:
```python
# Try disease ID instead of name
from tooluniverse.tools import OpenTargets_search_gwas_studies_by_disease

studies = OpenTargets_search_gwas_studies_by_disease(
    diseaseIds=["MONDO_0005148"],  # Type 2 diabetes
    size=10
)
```

### Missing genotypes
```python
result = calculate_personal_prs(prs, my_genotypes)
# Warning: Only using 5 of 50 SNPs
```

**Solution**: Check genotype platform coverage:
- 23andMe v5: ~600K SNPs
- Ancestry DNA: ~700K SNPs
- WGS: All SNPs covered

Consider imputation to fill in missing variants.

### Ancestry mismatch
```python
# European PRS applied to African ancestry
result = calculate_personal_prs(prs, african_genotypes)
# PRS may be inaccurate due to ancestry mismatch
```

**Solution**: Use ancestry-matched GWAS when available:
```python
# Check study ancestry
from tooluniverse.tools import gwas_get_study_by_id

study = gwas_get_study_by_id("GCST000392")
print(study.get('discovery_ancestry'))  # ['European']
```

## Next Steps

1. **Read SKILL.md** for comprehensive methodology and best practices
2. **Run test_skill_comprehensive.py** to see all features in action
3. **Explore PGS Catalog** (https://www.pgscatalog.org/) for validated PRS models
4. **Consider LD clumping** for production PRS (use PLINK or PRSice)
5. **Get genetic counseling** before clinical decisions

## Support

- **Documentation**: See SKILL.md for detailed methodology
- **Testing**: Run test_skill_comprehensive.py for validation
- **Issues**: Report bugs on ToolUniverse GitHub
- **Questions**: Consult genetic counselor for clinical interpretation

## Disclaimer

This tool is for educational and research purposes. For clinical genetic testing, consult certified genetic counselors and healthcare providers. PRS does not diagnose disease and should not replace medical advice.
