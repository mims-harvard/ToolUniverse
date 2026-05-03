# Variant Annotation Guide

Complete guide to annotating variants using ToolUniverse annotation tools.

## When to Use ToolUniverse Annotation

Use ToolUniverse annotation tools when you need:
1. **Clinical significance**: ClinVar pathogenicity classifications
2. **Population frequencies**: gnomAD, ExAC, 1000 Genomes allele frequencies
3. **Pathogenicity scores**: CADD, SIFT, PolyPhen predictions
4. **Gene/transcript information**: Ensembl gene IDs, transcript IDs, protein changes
5. **Consequence prediction**: When VCF lacks annotation

## Annotation Tools Overview

| Tool | Best For | Input Format | Response |
|------|---------|--------------|----------|
| `MyVariant_query_variants` | Batch annotation (recommended) | rsID or HGVS | ClinVar, dbSNP, gnomAD, CADD, SIFT, PolyPhen |
| `MyVariant_get_variant_annotation` | Single variant detail | HGVS | Full annotation object |
| `dbsnp_get_variant_by_rsid` | Population frequencies | rsID (rs12345) | Allele frequencies, clinical significance |
| `gnomad_get_variant` | gnomAD-specific data | CHR-POS-REF-ALT | gnomAD variant metadata |
| `EnsemblVEP_annotate_rsid` | Consequence prediction | rsID | Transcript consequences |
| `ensembl_vep_region` | Regional annotation | chr:start-end | All variants in region |

## Annotation Workflow

### Step 1: Parse VCF and Extract rsIDs

```python
from python_implementation import parse_vcf

vcf_data = parse_vcf("variants.vcf")

# Extract variants with rsIDs (most reliable for annotation)
rsid_variants = [v for v in vcf_data.variants if v.vid and v.vid.startswith('rs')]
print(f"Found {len(rsid_variants)} variants with rsIDs")
```

### Step 2: Batch Annotate with MyVariant.info

**MyVariant.info is recommended** because it aggregates multiple sources in one call.

```python
from tooluniverse import ToolUniverse
from python_implementation import batch_annotate_variants

# Load ToolUniverse
tu = ToolUniverse()
tu.load_tools()

# Annotate up to 100 variants
annotations = batch_annotate_variants(
    tu,
    vcf_data.variants,
    max_annotate=100  # Respect rate limits
)

# Process annotations
for ann in annotations:
    print(f"{ann.variant_key} - {ann.gene_symbol}")
    print(f"  ClinVar: {ann.clinvar_classification}")
    print(f"  gnomAD AF: {ann.gnomad_af}")
    print(f"  CADD: {ann.cadd_phred}")
```

### Step 3: Query Specific Tools for Additional Data

For specific use cases, query tools directly:

```python
# Get detailed population frequencies from dbSNP
dbsnp_result = tu.execute_tool("dbsnp_get_variant_by_rsid", rsid="rs699")

# Get gnomAD-specific data
gnomad_result = tu.execute_tool("gnomad_get_variant", variant_id="1-55039974-G-A")

# Get VEP consequence prediction
vep_result = tu.execute_tool("EnsemblVEP_annotate_rsid", variant_id="rs699")
```

## MyVariant.info Annotation

### Query Variants (Batch)

**Best for**: Annotating multiple variants at once

```python
# Query by rsID
result = tu.execute_tool("MyVariant_query_variants", query="rs699 rs334")

# Query by HGVS
result = tu.execute_tool("MyVariant_query_variants", query="chr7:g.140753336A>T")
```

**Response structure**:
```json
{
  "data": {
    "hits": [
      {
        "_id": "chr7:g.140753336A>T",
        "dbsnp": {
          "rsid": "rs113488022",
          "gene": {"symbol": "BRAF"}
        },
        "clinvar": {
          "rcv": {
            "clinical_significance": "Pathogenic",
            "conditions": {"name": "Melanoma, malignant"}
          }
        },
        "gnomad_genome": {
          "af": {"af": 0.000008}
        },
        "cadd": {
          "phred": 34.0
        }
      }
    ]
  }
}
```

### Get Variant Annotation (Single)

**Best for**: Detailed information on one variant

```python
result = tu.execute_tool("MyVariant_get_variant_annotation", variant_id="chr7:g.140753336A>T")
```

### Extracted Fields

From MyVariant.info response, we extract:

| Field | Path | Description |
|-------|------|-------------|
| rsID | `dbsnp.rsid` | dbSNP identifier |
| Gene symbol | `dbsnp.gene.symbol` | Gene name |
| ClinVar classification | `clinvar.rcv.clinical_significance` | Pathogenicity |
| ClinVar disease | `clinvar.rcv.conditions.name` | Associated condition |
| gnomAD allele frequency | `gnomad_genome.af.af` | Population frequency |
| CADD PHRED | `cadd.phred` | Deleteriousness score |
| SIFT prediction | `cadd.sift.pred` | Functional prediction |
| PolyPhen prediction | `cadd.polyphen.pred` | Functional prediction |
| Protein change | `dbsnp.gene.hgvs_c` | HGVS protein notation |

## dbSNP Annotation

### Get Variant by rsID

**Best for**: Detailed population frequencies

```python
result = tu.execute_tool("dbsnp_get_variant_by_rsid", rsid="rs699")
```

**Response structure**:
```json
{
  "status": "success",
  "data": {
    "rsid": "rs699",
    "chromosome": "1",
    "position": 230710048,
    "allele_frequencies": {
      "1000Genomes": {"G": 0.7432, "A": 0.2568},
      "gnomAD_exome": {"G": 0.75, "A": 0.25},
      "TOPMED": {"G": 0.76, "A": 0.24}
    },
    "clinical_significance": ["benign"],
    "gene": "AGT",
    "hgvs": "NC_000001.11:g.230710048G>A"
  }
}
```

### Extracted Fields

| Field | Description |
|-------|-------------|
| `allele_frequencies` | Frequencies from 1000G, gnomAD, ExAC, TOPMED |
| `clinical_significance` | ClinVar classifications |
| `gene` | Associated gene |
| `hgvs` | HGVS notation |

## gnomAD Annotation

### Get Variant

**Best for**: gnomAD-specific metadata

```python
result = tu.execute_tool("gnomad_get_variant", variant_id="1-55039974-G-A")
```

**Note**: This tool returns basic metadata only. For allele frequencies, use MyVariant.info instead.

**Response structure**:
```json
{
  "status": "success",
  "data": {
    "data": {
      "variant": {
        "variant_id": "1-55039974-G-A",
        "chrom": "1",
        "pos": 55039974,
        "ref": "G",
        "alt": "A"
      }
    }
  }
}
```

## Ensembl VEP Annotation

### Annotate by rsID

**Best for**: Consequence prediction

```python
result = tu.execute_tool("EnsemblVEP_annotate_rsid", variant_id="rs699")
```

**Response format varies**:
- May return list of consequences
- May return `{data, metadata}` wrapper
- May return `{error}` if variant not found

**Handle all cases**:
```python
if isinstance(result, dict):
    if 'error' in result:
        print("Variant not found")
    elif 'data' in result:
        consequences = result['data']
else:
    consequences = result
```

### Annotate by Region

**Best for**: Annotating all variants in a genomic region

```python
result = tu.execute_tool(
    "ensembl_vep_region",
    region="7:140753336-140753336",
    species="human"
)
```

## Practical Examples

### Example 1: Clinical Variant Screening

Find all pathogenic/likely pathogenic variants:

```python
from python_implementation import parse_vcf, batch_annotate_variants
from tooluniverse import ToolUniverse

# Parse VCF
vcf_data = parse_vcf("patient.vcf")

# Load ToolUniverse
tu = ToolUniverse()
tu.load_tools()

# Annotate variants with rsIDs
rsid_variants = [v for v in vcf_data.variants if v.vid and v.vid.startswith('rs')]
annotations = batch_annotate_variants(tu, rsid_variants, max_annotate=100)

# Find pathogenic variants
pathogenic = [
    a for a in annotations
    if a.clinvar_classification and 'pathogenic' in a.clinvar_classification.lower()
]

print(f"Found {len(pathogenic)} pathogenic variants:")
for a in pathogenic:
    print(f"  {a.variant_key} - {a.gene_symbol}")
    print(f"    Classification: {a.clinvar_classification}")
    print(f"    gnomAD AF: {a.gnomad_af}")
    print(f"    CADD: {a.cadd_phred}")
```

### Example 2: Population Frequency Analysis

Find rare variants (AF < 1%):

```python
annotations = batch_annotate_variants(tu, vcf_data.variants, max_annotate=100)

rare = [a for a in annotations if a.gnomad_af is not None and a.gnomad_af < 0.01]

print(f"Found {len(rare)} rare variants (AF < 1%):")
for a in rare:
    print(f"  {a.variant_key} - {a.gene_symbol}")
    print(f"    AF: {a.gnomad_af}")
```

### Example 3: Pathogenicity Score Filtering

Find high CADD score variants (top 1% most deleterious):

```python
annotations = batch_annotate_variants(tu, vcf_data.variants, max_annotate=100)

high_cadd = [a for a in annotations if a.cadd_phred is not None and a.cadd_phred >= 20]

print(f"Found {len(high_cadd)} high CADD score variants (≥20):")
for a in high_cadd:
    print(f"  {a.variant_key} - {a.gene_symbol} - {a.mutation_type}")
    print(f"    CADD: {a.cadd_phred}")
```

### Example 4: Compare ClinVar with Population Frequency

Find variants classified as pathogenic but common in population (potential reclassification candidates):

```python
annotations = batch_annotate_variants(tu, vcf_data.variants, max_annotate=100)

conflicting = [
    a for a in annotations
    if a.clinvar_classification and 'pathogenic' in a.clinvar_classification.lower()
    and a.gnomad_af is not None and a.gnomad_af > 0.01  # Common (>1%)
]

print(f"Found {len(conflicting)} variants with conflicting evidence:")
for a in conflicting:
    print(f"  {a.variant_key} - {a.gene_symbol}")
    print(f"    ClinVar: {a.clinvar_classification}")
    print(f"    gnomAD AF: {a.gnomad_af} (common)")
```

## Annotation Report

Generate a comprehensive annotation report:

```python
from python_implementation import variant_analysis_pipeline

report = variant_analysis_pipeline(
    vcf_path="variants.vcf",
    output_file="annotated_report.md",
    annotate=True,
    max_annotate=50  # Annotate top 50 variants
)
```

**Report includes**:
1. Variant Annotations table with:
   - Variant ID
   - Gene
   - Mutation type
   - ClinVar classification
   - gnomAD AF
   - CADD score
2. Clinical Significance distribution
3. Top mutated genes
4. Summary statistics

## Best Practices

### 1. Annotate Variants with rsIDs First

rsIDs are the most reliable identifiers:

```python
# Prioritize variants with rsIDs
rsid_variants = [v for v in vcf_data.variants if v.vid and v.vid.startswith('rs')]
annotations = batch_annotate_variants(tu, rsid_variants, max_annotate=100)
```

### 2. Use MyVariant.info for Batch Annotation

MyVariant.info aggregates multiple sources in one call:
- ClinVar
- dbSNP
- gnomAD
- CADD
- SIFT
- PolyPhen

### 3. Respect Rate Limits

Limit batch annotation to 50-100 variants at a time:

```python
annotations = batch_annotate_variants(tu, variants, max_annotate=100)
```

### 4. Handle Missing Data

Not all variants have all annotations:

```python
for ann in annotations:
    if ann.clinvar_classification:
        print(f"ClinVar: {ann.clinvar_classification}")
    else:
        print("ClinVar: No data")

    if ann.gnomad_af is not None:
        print(f"gnomAD AF: {ann.gnomad_af}")
    else:
        print("gnomAD AF: Not available")
```

### 5. Combine with Filtering

Annotate only high-quality variants:

```python
from python_implementation import filter_variants, FilterCriteria

# Filter first
criteria = FilterCriteria(min_depth=20, pass_only=True)
passing, failing = filter_variants(vcf_data.variants, criteria)

# Then annotate
annotations = batch_annotate_variants(tu, passing, max_annotate=50)
```

## Troubleshooting

### Issue: "No annotation found"

**Cause**: Variant not in database or wrong identifier format

**Solution**:
- Verify rsID is correct (rs12345)
- Try HGVS format (chr7:g.140753336A>T)
- Check if variant is in dbSNP/ClinVar

### Issue: Empty ClinVar classification

**Cause**: Variant has no ClinVar submission

**Solution**: This is normal. Not all variants have clinical significance data.

### Issue: Missing gnomAD allele frequency

**Cause**: Variant not in gnomAD (very rare or not covered)

**Solution**: Consider as potentially rare/novel variant

### Issue: Rate limiting errors

**Cause**: Too many API requests

**Solution**: Reduce `max_annotate` parameter or add delays between batches

## Advanced: Custom Annotation Pipeline

Build a custom annotation pipeline:

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

def annotate_variant_full(variant):
    """Get comprehensive annotation from multiple sources"""

    annotation = {
        'variant_id': variant.vid,
        'chrom': variant.chrom,
        'pos': variant.pos,
        'ref': variant.ref,
        'alt': variant.alt
    }

    # MyVariant.info (primary)
    if variant.vid and variant.vid.startswith('rs'):
        myvariant = tu.execute_tool("MyVariant_query_variants", query=variant.vid)
        if myvariant.get('data', {}).get('hits'):
            hit = myvariant['data']['hits'][0]
            annotation['clinvar'] = hit.get('clinvar', {})
            annotation['gnomad'] = hit.get('gnomad_genome', {})
            annotation['cadd'] = hit.get('cadd', {})

    # dbSNP (supplemental)
    if variant.vid and variant.vid.startswith('rs'):
        dbsnp = tu.execute_tool("dbsnp_get_variant_by_rsid", rsid=variant.vid)
        if dbsnp.get('status') == 'success':
            annotation['allele_frequencies'] = dbsnp['data'].get('allele_frequencies', {})

    return annotation

# Use on variants
for variant in vcf_data.variants[:10]:
    full_annotation = annotate_variant_full(variant)
    print(full_annotation)
```
