---
name: tooluniverse-variant-analysis
description: Production-ready VCF processing, variant annotation, mutation analysis, and structural variant (SV/CNV) interpretation for bioinformatics questions. Parses VCF files (streaming, large files), classifies mutation types (missense, nonsense, synonymous, frameshift, splice, intronic, intergenic) and structural variants (deletions, duplications, inversions, translocations), applies VAF/depth/quality/consequence filters, annotates with ClinVar/dbSNP/gnomAD/CADD via ToolUniverse, interprets SV/CNV clinical significance using ClinGen dosage sensitivity scores, computes variant statistics, and generates reports. Solves questions like "What fraction of variants with VAF < 0.3 are missense?", "How many non-reference variants remain after filtering intronic/intergenic?", "What is the pathogenicity of this deletion affecting BRCA1?", or "Which dosage-sensitive genes overlap this CNV?". Use when processing VCF files, annotating variants, filtering by VAF/depth/consequence, classifying mutations, interpreting structural variants, assessing CNV pathogenicity, comparing cohorts, or answering variant analysis questions.
---

# Variant Analysis and Annotation

Production-ready VCF processing and variant annotation skill combining local bioinformatics computation with ToolUniverse database integration. Designed to answer bioinformatics analysis questions about VCF data, mutation classification, variant filtering, and clinical annotation.

## Domain Reasoning

VCF quality filtering must come before interpretation. A variant called at 2x read depth is unreliable regardless of its QUAL score, because stochastic sequencing errors at low depth can mimic true variants. The recommended minimums — depth > 10x, QUAL > 20, allele frequency consistent with expected zygosity — are not conservative; they are the floor below which calls cannot be trusted. Applying lenient filters to "keep more variants" sacrifices accuracy for coverage and produces false positives that propagate through all downstream analyses.

## LOOK UP DON'T GUESS

- Clinical significance of specific variants: query `MyVariant_query_variants` or `EnsemblVEP_annotate_rsid`; never cite ClinVar classifications from memory.
- Population allele frequencies: retrieve from MyVariant.info or gnomAD tools; do not assume rarity.
- ClinGen dosage sensitivity scores for genes in a CNV: call `ClinGen_dosage_by_gene`; do not estimate HI/TS scores.
- Mutation consequence predictions: run Ensembl VEP or retrieve from MyVariant.info; do not classify impact without tool output.

---

## CRISPR sgRNA Design Reasoning

- PAM sequence (NGG for SpCas9) must lie 3' of the target on the non-target strand; the guide RNA targets the 20 nt immediately upstream of the PAM
- For exon targeting: choose guides that cut early in the coding sequence for maximum frameshift/disruption
- Off-target risk increases with fewer mismatches; always check for genomic sites with 0-3 mismatches to the guide

---

## When to Use This Skill

**Triggers**:
- User provides a VCF file (SNV/indel or SV) and asks questions about its contents
- Questions about variant allele frequency (VAF) filtering
- Mutation type classification queries (missense, nonsense, synonymous, etc.)
- Structural variant interpretation requests (deletions, duplications, CNVs)
- Variant annotation requests (ClinVar, gnomAD, CADD, dbSNP)
- CNV pathogenicity assessment using ClinGen dosage sensitivity
- Cohort comparison questions
- Population frequency filtering (SNVs or SVs)
- Intronic/intergenic variant filtering
- Gene dosage sensitivity queries

**Example Questions**:
- "What fraction of variants with VAF < 0.3 are annotated as missense mutations?"
- "After filtering intronic/intergenic variants, how many non-reference variants remain?"
- "What is the clinical significance of this deletion affecting BRCA1?"
- "Which dosage-sensitive genes overlap this 500kb duplication on chr17?"
- "How many variants have clinical significance annotations?"
- "Compare variant counts between samples"

---

## Core Capabilities

| Capability | Description |
|-----------|-------------|
| **VCF Parsing** | Pure Python + cyvcf2 parsers. VCF 4.x, gzipped, multi-sample, SNV/indel/SV |
| **Mutation Classification** | Maps SO terms, SnpEff ANN, VEP CSQ, GATK Funcotator to standard types |
| **VAF Extraction** | Handles AF, AD, AO/RO, NR/NV, INFO AF formats |
| **Filtering** | VAF, depth, quality, PASS, variant type, mutation type, consequence, chromosome, SV size |
| **Statistics** | Ti/Tv ratio, per-sample VAF/depth stats, mutation type distribution, SV size distribution |
| **Annotation** | MyVariant.info (aggregates ClinVar, dbSNP, gnomAD, CADD, SIFT, PolyPhen) |
| **SV/CNV Analysis** | gnomAD SV population frequencies, DGVa/dbVar known SVs, ClinGen dosage sensitivity |
| **Clinical Interpretation** | ACMG/ClinGen CNV pathogenicity classification using haploinsufficiency/triplosensitivity scores |
| **DataFrame** | Convert to pandas for advanced analytics |
| **Reporting** | Markdown reports with tables and statistics, SV clinical reports |

---

## Workflow Overview

**Phase 1: Parse VCF** → Extract CHROM/POS/REF/ALT/QUAL/FILTER/INFO, per-sample GT/VAF/depth, annotations (ANN/CSQ/FUNCOTATION). Pure Python or cyvcf2.

**Phase 2: Classify** → Variant type (SNV/INS/DEL/MNV/SV), mutation type (missense/nonsense/synonymous/frameshift/splice/etc.), impact (HIGH/MODERATE/LOW/MODIFIER).

**Phase 3: Filter** → VAF range, depth, quality, PASS, variant/mutation type, consequence exclusion, population frequency, chromosome, SV size.

**Phase 4: Statistics** → Type/mutation/impact/chromosome distributions, Ti/Tv ratio, per-sample VAF/depth, gene mutation counts.

**Phase 5: Annotate** (optional) → MyVariant.info (ClinVar/dbSNP/gnomAD/CADD), Ensembl VEP consequence prediction.

**Phase 6: Report** → Markdown tables, direct answers, DataFrame export.

**Phase 7: SV/CNV Analysis** (if applicable) → gnomAD SV frequencies, ClinGen dosage sensitivity, ACMG pathogenicity classification.

---

## Phase Summaries

### Phase 1: VCF Parsing

**Use pandas for**:
- Reading VCF as structured data
- Quick exploratory analysis
- When you need to manipulate columns and rows

**Use python_implementation tools for**:
- Production parsing with annotation extraction
- Multi-sample VCF handling
- VAF extraction from FORMAT fields
- Large file streaming

**Key functions**:
```python
vcf_data = parse_vcf("input.vcf")           # Pure Python (always works)
vcf_data = parse_vcf_cyvcf2("input.vcf")    # Fast C-based (if installed)
df = variants_to_dataframe(vcf_data.variants, sample="TUMOR")  # For pandas
```

### Phase 2: Variant Classification

**Automatic classification from annotations**:
- SnpEff ANN field
- VEP CSQ field
- GATK Funcotator FUNCOTATION field
- Standard INFO keys: EFFECT, EFF, TYPE

**Mutation types supported**: missense, nonsense, synonymous, frameshift, splice_site, splice_region, inframe_insertion, inframe_deletion, intronic, intergenic, UTR_5, UTR_3, upstream, downstream, stop_lost, start_lost

**See references/mutation_classification_guide.md for full details**

### Phase 3: Filtering

**Common filtering patterns**:
```python
# Somatic-like variants
criteria = FilterCriteria(
    min_vaf=0.05, max_vaf=0.95,
    min_depth=20, pass_only=True,
    exclude_consequences=["intronic", "intergenic", "upstream", "downstream"]
)

# High-confidence germline
criteria = FilterCriteria(
    min_vaf=0.25, min_depth=30, pass_only=True,
    chromosomes=["1", "2", ..., "22", "X", "Y"]
)

# Rare pathogenic candidates
criteria = FilterCriteria(
    min_depth=20, pass_only=True,
    mutation_types=["missense", "nonsense", "frameshift"]
)
```

**See references/vcf_filtering.md for all filter options**

### Phase 4-6: Statistics, Annotation, Reporting

Use python_implementation for standard stats (Ti/Tv, type distributions, per-sample VAF/depth); pandas for custom aggregations. For annotation, prefer MyVariant.info (batch: ClinVar + dbSNP + gnomAD + CADD); limit to 50-100 variants per batch. Reports include type/mutation/impact/chromosome distributions, VAF stats, clinical significance, and top mutated genes.

**See references/annotation_guide.md for detailed examples**

### Phase 7: Structural Variant & CNV Analysis

**When VCF contains SV calls** (SVTYPE=DEL/DUP/INV/BND):

1. **Identify affected genes** (from VCF annotation or coordinate overlap)
2. **Query ClinGen dosage sensitivity**:
   ```python
   clingen = ClinGen_dosage_by_gene(gene_symbol="BRCA1")
   # Returns: haploinsufficiency_score, triplosensitivity_score
   ```
3. **Check population frequency**:
   ```python
   gnomad_sv = gnomad_get_sv_by_gene(gene_symbol="BRCA1")
   # Returns: SVs with AF, AC, AN
   ```
4. **Classify pathogenicity**:
   - Pathogenic: Deletion + HI score = 3, AF < 0.0001
   - Likely Pathogenic: Deletion + HI score = 2, AF < 0.001
   - VUS: HI/TS score = 0-1, AF 0.001-0.01
   - Benign: AF > 0.01

**ClinGen dosage score interpretation**:
- **3**: Sufficient evidence for dosage pathogenicity (HIGH impact)
- **2**: Some evidence (MODERATE impact)
- **1**: Little evidence (LOW impact)
- **0**: No evidence (MINIMAL impact)
- **40**: Dosage sensitivity unlikely

**See references/sv_cnv_analysis.md for full SV workflow**

---

## Answering BixBench Questions

### Pattern 1: VAF + Mutation Type Fraction

**Question**: "What fraction of variants with VAF < X are annotated as Y mutations?"

```python
result = answer_vaf_mutation_fraction(
    vcf_path="input.vcf",
    max_vaf=0.3,
    mutation_type="missense",
    sample="TUMOR"
)
# Returns: fraction, total_below_vaf, matching_mutation_type
```

### Pattern 2: Cohort Comparison

**Question**: "What is the difference in mutation frequency between cohorts?"

```python
result = answer_cohort_comparison(
    vcf_paths=["cohort1.vcf", "cohort2.vcf"],
    mutation_type="missense",
    cohort_names=["Treatment", "Control"]
)
# Returns: cohorts, frequency_difference
```

### Pattern 3: Filter and Count

**Question**: "After filtering X, how many Y remain?"

```python
result = answer_non_reference_after_filter(
    vcf_path="input.vcf",
    exclude_intronic_intergenic=True
)
# Returns: total_input, non_reference, remaining
```

---

## ToolUniverse Tools Reference

### SNV/Indel Annotation

| Tool | When to Use | Parameters | Response |
|------|------------|------------|----------|
| `MyVariant_query_variants` | Batch annotation | `query` (rsID/HGVS) | ClinVar, dbSNP, gnomAD, CADD |
| `dbsnp_get_variant_by_rsid` | Population frequencies | `rsid` | Frequencies, clinical significance |
| `gnomad_get_variant` | gnomAD metadata | `variant_id` (CHR-POS-REF-ALT) | Basic variant info |
| `EnsemblVEP_annotate_rsid` | Consequence prediction | `variant_id` (rsID) | Transcript impact |

### Structural Variant Annotation

| Tool | When to Use | Parameters | Response |
|------|------------|------------|----------|
| `gnomad_get_sv_by_gene` | SV population frequency | `gene_symbol` | SVs with AF, AC, AN |
| `gnomad_get_sv_by_region` | Regional SV search | `chrom`, `start`, `end` | SVs in region |
| `ClinGen_dosage_by_gene` | Dosage sensitivity | `gene_symbol` | HI/TS scores, disease |
| `ClinGen_dosage_region_search` | Dosage-sensitive genes in region | `chromosome`, `start`, `end` | All genes with HI/TS scores |
| `ensembl_get_structural_variants` | Known SVs from DGVa/dbVar | `chrom`, `start`, `end`, `species` | Clinical significance |

**See references/annotation_guide.md for detailed tool usage examples**

---

## Common Use Patterns

```python
# Quick summary
report = variant_analysis_pipeline("input.vcf", output_file="report.md")

# Filtered analysis
report = variant_analysis_pipeline("input.vcf",
    filters=FilterCriteria(min_vaf=0.1, min_depth=20, pass_only=True))

# Annotated report (top 50 variants with ClinVar/gnomAD/CADD)
report = variant_analysis_pipeline("input.vcf", annotate=True, max_annotate=50)
```

**pandas vs python_implementation**: Use python_implementation for parsing/classification/annotation, then convert to DataFrame for custom aggregations:

```python
vcf_data = parse_vcf("input.vcf")
passing, _ = filter_variants(vcf_data.variants, criteria)
df = variants_to_dataframe(passing, sample="TUMOR")
```

---

## Limitations

- **VCF annotation required for mutation classification**: If VCF has no ANN/CSQ/FUNCOTATION in INFO, mutation types will be "unknown" until ToolUniverse annotation is applied
- **Multi-allelic variants**: Parser takes first ALT allele for type classification
- **ToolUniverse annotation rate**: API-based, limited to ~100 variants per batch by default to respect rate limits
- **gnomAD tool**: Returns basic metadata only (not full allele frequencies); use MyVariant.info for gnomAD AF
- **Large VCFs**: Pure Python parser streams line-by-line; cyvcf2 is recommended for files with >100K variants

---

## Reference Documentation

- **references/vcf_filtering.md**: Complete filter options and examples
- **references/mutation_classification_guide.md**: Detailed mutation type classification rules
- **references/annotation_guide.md**: ToolUniverse annotation workflows with examples
- **references/sv_cnv_analysis.md**: Complete SV/CNV interpretation workflow

---

## Additional Resources

- Scripts: `scripts/parse_vcf.py`, `scripts/filter_variants.py`, `scripts/annotate_variants.py`
- Quick start recipes and MCP examples: `QUICK_START.md`
