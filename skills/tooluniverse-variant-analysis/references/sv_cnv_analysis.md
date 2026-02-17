# Structural Variant and CNV Analysis Guide

Complete workflow for interpreting structural variants (deletions, duplications, inversions, translocations) and copy number variants using ToolUniverse.

## When to Use This Workflow

- VCF contains SV calls (from Manta, Delly, LUMPY, etc.)
- BED file with CNV regions
- Coordinate-based SV queries (chr17:43044295-43070295)
- Gene-based SV queries ("What SVs affect BRCA1?")
- Clinical interpretation of CNV pathogenicity

## SV Analysis Workflow

```
Input: SV VCF or coordinates
    |
    v
Step 1: Identify Structural Variants
    |-- Detect SVTYPE (DEL, DUP, INV, BND, CNV)
    |-- Extract coordinates (chrom, start, end)
    |-- Determine size
    |
    v
Step 2: Annotate with Population Frequencies
    |-- Query gnomAD SV by gene or region
    |-- Get allele frequency (AF), allele count (AC), allele number (AN)
    |-- Interpret frequency (common vs rare)
    |
    v
Step 3: Query Known SVs from DGVa/dbVar
    |-- Use Ensembl to find reported SVs
    |-- Get clinical significance
    |
    v
Step 4: Identify Affected Genes
    |-- From gnomAD response
    |-- From VCF annotation
    |-- From coordinate overlap
    |
    v
Step 5: Query ClinGen Dosage Sensitivity
    |-- For each affected gene
    |-- Get haploinsufficiency (HI) score
    |-- Get triplosensitivity (TS) score
    |
    v
Step 6: Classify SV Pathogenicity
    |-- Combine evidence (dosage + frequency + literature)
    |-- Apply ACMG/ClinGen CNV guidelines
    |-- Classify: Pathogenic / Likely Pathogenic / VUS / Benign
    |
    v
Step 7: Generate SV Clinical Report
    |-- Summary (type, coordinates, size, frequency)
    |-- Affected genes (with dosage scores)
    |-- Clinical interpretation
    |-- Recommendations
```

## Step 1: Identify Structural Variants

### From VCF

SV callers (Manta, Delly, LUMPY) annotate SVs in VCF INFO field:

**VCF example**:
```
chr17  43044295  DEL_chr17_1  N  <DEL>  100  PASS  SVTYPE=DEL;END=43070295;SVLEN=-26000
```

**Detect SVs**:
- Check for SVTYPE in INFO (DEL, DUP, INV, BND, CNV)
- Check for large indels (|len(REF) - len(ALT)| > 50bp)
- Extract END coordinate
- Calculate size from SVLEN or (END - POS)

### From Coordinates

User provides coordinates: "chr17:43044295-43070295"

**Parse format**:
```python
import re

coord_str = "chr17:43044295-43070295"
match = re.match(r'chr(\w+):(\d+)-(\d+)', coord_str)
chrom = match.group(1)  # "17"
start = int(match.group(2))  # 43044295
end = int(match.group(3))    # 43070295
size = end - start           # 26000 bp
```

## Step 2: Query gnomAD SV Population Frequencies

### Query by Gene Symbol

**When to use**: When you know which gene is affected

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

result = tu.execute_tool("gnomad_get_sv_by_gene", gene_symbol="BRCA1")
```

**Response structure**:
```json
{
  "data": {
    "structural_variants": [
      {
        "variant_id": "DEL_chr17_24e4872b",
        "chrom": "17",
        "pos": 43044295,
        "end": 43070295,
        "sv_type": "DEL",
        "size": 26000,
        "af": 0.000008,
        "ac": 3,
        "an": 375000,
        "filters": ["PASS"],
        "genes": ["BRCA1"]
      }
    ]
  }
}
```

### Query by Genomic Region

**When to use**: When you have coordinates but not gene

```python
result = tu.execute_tool(
    "gnomad_get_sv_by_region",
    chrom="17",
    start=43044295,
    end=43070295
)
```

### Query Specific SV Details

**When to use**: When you have a gnomAD SV ID

```python
result = tu.execute_tool("gnomad_get_sv_detail", sv_id="DEL_chr17_24e4872b")
```

**Response includes**:
- Quality metrics (QUAL, GQ)
- Filter status
- Detailed population frequencies

### Frequency Interpretation

| gnomAD AF | Interpretation | Clinical Impact |
|-----------|---------------|-----------------|
| **AF > 0.01** (1%) | Common benign variant | Likely benign |
| **AF 0.001-0.01** | Low-frequency variant | Uncertain, context-dependent |
| **AF < 0.001** (0.1%) | Rare variant | Potentially pathogenic if affects critical gene |
| **Not in gnomAD** | Very rare or novel | Unknown, requires additional evidence |

## Step 3: Query Known SVs from DGVa/dbVar

Use Ensembl to find previously reported SVs:

### Query by Region

```python
result = tu.execute_tool(
    "ensembl_get_structural_variants",
    chrom="17",
    start=43044295,
    end=43070295,
    species="human"
)
```

**Response structure**:
```json
{
  "data": [
    {
      "id": "esv3647486",
      "var_class": "copy_number_variation",
      "clinical_significance": ["pathogenic", "likely_pathogenic"],
      "evidence": ["1000 Genomes", "dbVar"],
      "study": "estd199",
      "sample_count": 4
    }
  ]
}
```

### Get SV Details

```python
result = tu.execute_tool(
    "ensembl_get_sv_detail",
    sv_id="esv3647486",
    species="human"
)
```

## Step 4: Identify Affected Genes

### From gnomAD Response

gnomAD SV response includes `genes` field:

```python
result = tu.execute_tool("gnomad_get_sv_by_region", chrom="17", start=43044295, end=43070295)
sv = result['data']['structural_variants'][0]
affected_genes = sv['genes']  # ["BRCA1"]
```

### From VCF Annotation

Some SV callers annotate genes in INFO:

```
SVTYPE=DEL;END=43070295;GENES=BRCA1,NBR2
```

### From Coordinate Overlap

If genes not provided, query by coordinates to find overlapping genes.

## Step 5: Query ClinGen Dosage Sensitivity

For each affected gene, determine if it's dosage-sensitive.

### Query by Gene Symbol

```python
result = tu.execute_tool("ClinGen_dosage_by_gene", gene_symbol="BRCA1")
```

**Response structure**:
```json
{
  "data": {
    "gene_symbol": "BRCA1",
    "haploinsufficiency_score": 3,
    "triplosensitivity_score": 0,
    "dosage_sensitivity_disease": "Breast-ovarian cancer, familial 1",
    "haploinsufficiency_description": "Sufficient evidence for dosage pathogenicity",
    "triplosensitivity_description": "No evidence available",
    "pli_score": 0.00,
    "loeuf": 0.46,
    "acmg_secondary_findings": true
  }
}
```

### Query by Region

Find all dosage-sensitive genes in a region:

```python
result = tu.execute_tool(
    "ClinGen_dosage_region_search",
    chromosome="17",
    start=43044295,
    end=43070295
)
```

**Response structure**:
```json
{
  "data": {
    "genes": [
      {
        "gene_symbol": "BRCA1",
        "haploinsufficiency_score": 3,
        "triplosensitivity_score": 0
      }
    ]
  }
}
```

### Dosage Score Interpretation

| Score | HI Meaning | TS Meaning | Clinical Impact |
|-------|-----------|------------|-----------------|
| **3** | Sufficient evidence | Sufficient evidence | **HIGH** - Established dosage sensitivity |
| **2** | Some evidence | Some evidence | **MODERATE** - Emerging evidence |
| **1** | Little evidence | Little evidence | **LOW** - Minimal evidence |
| **0** | No evidence | No evidence | **MINIMAL** - No known dosage effect |
| **30** | Gene associated with AD condition | - | **HIGH** (alternative scoring) |
| **40** | Dosage sensitivity unlikely | Dosage sensitivity unlikely | **MINIMAL** |

## Step 6: Classify SV Pathogenicity

Combine evidence to classify using ACMG/ClinGen CNV guidelines:

### Pathogenic Criteria

**Report as disease-causing if**:
- Deletion + HI score = 3 (sufficient evidence for haploinsufficiency)
- Duplication + TS score = 3 (sufficient evidence for triplosensitivity)
- gnomAD AF < 0.0001 (very rare)
- Gene is in ACMG Secondary Findings list
- Known pathogenic SV from ClinVar/dbVar with same breakpoints

### Likely Pathogenic Criteria

- Deletion + HI score = 2 (some evidence)
- Duplication + TS score = 2 (some evidence)
- gnomAD AF < 0.001
- Overlaps known pathogenic region but different breakpoints
- Disrupts critical functional domain

### Uncertain Significance (VUS) Criteria

- HI/TS score = 0 or 1 (no/little evidence)
- gnomAD AF 0.001-0.01 (conflicting frequency data)
- Affects gene but unclear clinical relevance
- Novel SV not in databases

### Likely Benign Criteria

- gnomAD AF > 0.01 (common in population)
- HI/TS score = 40 (dosage sensitivity unlikely)
- Does not affect any coding genes
- Matches known benign SV

### Benign Criteria

- gnomAD AF > 0.05 (very common)
- No overlap with any genes or regulatory regions
- Established benign variant in ClinVar

## Step 7: Generate SV Clinical Report

### Report Template

```markdown
# Structural Variant Clinical Report

## Variant Summary
- **Type**: Deletion (DEL)
- **Location**: chr17:43,044,295-43,070,295 (hg38)
- **Size**: 26 kb
- **Gene(s) Affected**: BRCA1 (complete deletion)

## Population Frequency
- **gnomAD AF**: 0.000008 (8 in 1 million)
- **Allele Count**: 3 / 375,000
- **Filter**: PASS
- **Interpretation**: Very rare variant

## ClinGen Dosage Sensitivity
- **Gene**: BRCA1
- **Haploinsufficiency Score**: 3 (Sufficient evidence)
- **Triplosensitivity Score**: 0 (No evidence)
- **Disease**: Breast-ovarian cancer, familial 1 (OMIM #604370)
- **ACMG Secondary Findings**: Yes

## Clinical Significance
**Classification**: PATHOGENIC

**Evidence**:
1. Complete deletion of BRCA1 gene
2. ClinGen HI score = 3 (established haploinsufficiency)
3. BRCA1 is ACMG Secondary Findings gene
4. Very rare in population (AF < 0.0001)
5. Known mechanism for hereditary breast/ovarian cancer

**ACMG/ClinGen Criteria Met**:
- Loss-of-function mechanism established (PVS1-equivalent)
- Haploinsufficiency score = 3 (dosage-sensitive gene)
- Absence/rarity in population databases

## Clinical Recommendations
1. **Genetic Counseling**: Strongly recommended
2. **Cancer Risk Management**: Enhanced surveillance per NCCN guidelines
   - Annual breast MRI starting age 25-30
   - Consider risk-reducing mastectomy
   - Consider risk-reducing salpingo-oophorectomy age 35-40
3. **Family Testing**: Cascade testing for first-degree relatives
4. **Confirmation**: MLPA or chromosomal microarray
```

## Complete Example Workflow

### Example 1: BRCA1 Deletion

**Input**: User asks "What is the clinical significance of a deletion affecting BRCA1?"

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

# Step 1: Query gnomAD SVs by gene
gnomad_result = tu.execute_tool("gnomad_get_sv_by_gene", gene_symbol="BRCA1")

# Extract first deletion
svs = gnomad_result['data']['structural_variants']
deletions = [sv for sv in svs if sv['sv_type'] == 'DEL']

if deletions:
    sv = deletions[0]
    print(f"Found deletion: {sv['variant_id']}")
    print(f"  Location: chr{sv['chrom']}:{sv['pos']}-{sv['end']}")
    print(f"  Size: {sv['size']} bp")
    print(f"  AF: {sv['af']}")

    # Step 2: Query ClinGen dosage sensitivity
    clingen_result = tu.execute_tool("ClinGen_dosage_by_gene", gene_symbol="BRCA1")
    dosage = clingen_result['data']

    print(f"\nClinGen Dosage Sensitivity:")
    print(f"  HI Score: {dosage['haploinsufficiency_score']}")
    print(f"  TS Score: {dosage['triplosensitivity_score']}")
    print(f"  Disease: {dosage['dosage_sensitivity_disease']}")
    print(f"  ACMG Secondary Findings: {dosage['acmg_secondary_findings']}")

    # Step 3: Classify pathogenicity
    if sv['af'] < 0.0001 and dosage['haploinsufficiency_score'] == 3:
        classification = "PATHOGENIC"
    elif sv['af'] < 0.001 and dosage['haploinsufficiency_score'] >= 2:
        classification = "LIKELY PATHOGENIC"
    elif sv['af'] > 0.01:
        classification = "LIKELY BENIGN"
    else:
        classification = "UNCERTAIN SIGNIFICANCE"

    print(f"\nClassification: {classification}")
```

### Example 2: Regional CNV Analysis

**Input**: User provides coordinates "chr17:43044295-43070295"

```python
# Query region for SVs
gnomad_result = tu.execute_tool(
    "gnomad_get_sv_by_region",
    chrom="17",
    start=43044295,
    end=43070295
)

# Query region for dosage-sensitive genes
clingen_result = tu.execute_tool(
    "ClinGen_dosage_region_search",
    chromosome="17",
    start=43044295,
    end=43070295
)

# Analyze overlap
svs = gnomad_result['data']['structural_variants']
dosage_genes = clingen_result['data']['genes']

print(f"Found {len(svs)} SVs in region")
print(f"Found {len(dosage_genes)} dosage-sensitive genes")

for gene in dosage_genes:
    if gene['haploinsufficiency_score'] >= 2:
        print(f"\n{gene['gene_symbol']} is haploinsufficient (HI={gene['haploinsufficiency_score']})")
        print("  Deletions affecting this gene are likely pathogenic")
```

### Example 3: Batch SV Interpretation

**Input**: VCF with multiple SV calls

```python
# Parse SV VCF (pseudocode - actual implementation in python_implementation.py)
def interpret_sv_batch(sv_vcf_path):
    results = []

    # Parse SV VCF
    svs = parse_sv_vcf(sv_vcf_path)

    for sv in svs:
        # Get population frequency
        gnomad = tu.execute_tool(
            "gnomad_get_sv_by_region",
            chrom=sv.chrom,
            start=sv.start,
            end=sv.end
        )

        # Identify affected genes
        genes = sv.genes  # From VCF annotation or coordinate overlap

        # Query dosage sensitivity for each gene
        dosage_results = []
        for gene in genes:
            clingen = tu.execute_tool("ClinGen_dosage_by_gene", gene_symbol=gene)
            dosage_results.append(clingen['data'])

        # Classify pathogenicity
        classification = classify_sv_pathogenicity(
            sv_type=sv.type,
            gnomad_af=gnomad['data']['structural_variants'][0]['af'] if gnomad['data']['structural_variants'] else None,
            dosage_scores=dosage_results
        )

        results.append({
            'sv_id': sv.id,
            'classification': classification,
            'genes': genes,
            'gnomad_af': gnomad['data']['structural_variants'][0]['af'] if gnomad['data']['structural_variants'] else None,
            'dosage_sensitive_genes': [
                g['gene_symbol'] for g in dosage_results
                if g['haploinsufficiency_score'] >= 2 or g['triplosensitivity_score'] >= 2
            ]
        })

    return results
```

## SV Type-Specific Interpretation

### Deletions

**Check**: Haploinsufficiency (HI) scores

- HI = 3: Likely pathogenic (if rare)
- HI = 2: Possibly pathogenic (if very rare)
- HI = 0: Likely benign (unless affects multiple genes)

### Duplications

**Check**: Triplosensitivity (TS) scores

- TS = 3: Likely pathogenic (if rare)
- TS = 2: Possibly pathogenic (if very rare)
- TS = 0: Likely benign

### Inversions

**Check**: Gene disruption

- If breaks gene: Likely loss of function
- If no gene disruption: May affect regulatory elements
- Rare inversions affecting known disease genes: Potentially pathogenic

### Translocations

**Check**: Fusion genes, gene disruption

- Known oncogenic fusions (e.g., BCR-ABL): Pathogenic
- Disrupts tumor suppressor: Potentially pathogenic
- No gene involvement: Likely benign

## SV Size Considerations

| Size | Impact | Considerations |
|------|--------|---------------|
| **< 1 kb** | Usually low | May affect exons or regulatory elements |
| **1-50 kb** | Variable | Check if affects complete genes |
| **50 kb - 1 Mb** | Moderate-High | Likely affects multiple genes |
| **> 1 Mb** | High | Affects many genes, genomic instability |

## Key Considerations

### Recurrent CNV Regions

Some regions have well-established clinical significance:
- 22q11.2 deletion (DiGeorge syndrome)
- 15q11-q13 deletion (Prader-Willi / Angelman)
- 7q11.23 deletion (Williams syndrome)
- 17p11.2 deletion (Smith-Magenis syndrome)

For these regions, check established guidelines.

### De Novo vs Inherited

- **De novo SVs**: More likely pathogenic
- **Inherited from healthy parent**: Less likely pathogenic (unless incomplete penetrance)

### Breakpoint Precision

- SV callers report confidence intervals (CIPOS, CIEND)
- Precise breakpoints: Higher confidence in gene impact
- Imprecise breakpoints: May need confirmation

## Limitations

1. **Breakpoint resolution**: SV callers have limited precision
2. **Complex SVs**: May require case-by-case interpretation
3. **Regulatory regions**: Impact hard to predict
4. **Incomplete penetrance**: Pathogenic SVs may not always cause disease
5. **Database coverage**: Not all SVs are in gnomAD or DGVa

## Best Practices

1. Always check both population frequency AND dosage sensitivity
2. Consider gene function in disease context
3. Check for known pathogenic CNVs in ClinVar/OMIM
4. Recommend confirmatory testing (MLPA, microarray)
5. Provide genetic counseling for pathogenic findings
