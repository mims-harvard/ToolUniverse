---
name: tooluniverse-variant-analysis
description: Production-ready VCF processing, variant annotation, mutation analysis, and structural variant (SV/CNV) interpretation for bioinformatics questions. Parses VCF files (streaming, large files), classifies mutation types (missense, nonsense, synonymous, frameshift, splice, intronic, intergenic) and structural variants (deletions, duplications, inversions, translocations), applies VAF/depth/quality/consequence filters, annotates with ClinVar/dbSNP/gnomAD/CADD via ToolUniverse, interprets SV/CNV clinical significance using ClinGen dosage sensitivity scores, computes variant statistics, and generates reports. Solves questions like "What fraction of variants with VAF < 0.3 are missense?", "How many non-reference variants remain after filtering intronic/intergenic?", "What is the pathogenicity of this deletion affecting BRCA1?", or "Which dosage-sensitive genes overlap this CNV?". Use when processing VCF files, annotating variants, filtering by VAF/depth/consequence, classifying mutations, interpreting structural variants, assessing CNV pathogenicity, comparing cohorts, or answering variant analysis questions.
---

# Variant Analysis and Annotation

Production-ready VCF processing and variant annotation skill combining local bioinformatics computation with ToolUniverse database integration. Designed to answer bioinformatics analysis questions about VCF data, mutation classification, variant filtering, and clinical annotation.

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

**Example Questions This Skill Solves**:

*SNV/Indel Analysis:*
1. "What fraction of variants with VAF < 0.3 are annotated as missense mutations?"
2. "What is the difference in missense variant frequency between cohorts?"
3. "After filtering intronic/intergenic variants, how many non-reference variants remain?"
4. "How many high-impact variants are in this VCF?"
5. "Which gene has the most missense variants?"
6. "Compare variant counts between samples"
7. "What is the Ti/Tv ratio?"
8. "How many variants have clinical significance annotations?"

*Structural Variant Analysis (NEW):*
9. "What is the clinical significance of this deletion affecting BRCA1?"
10. "Which dosage-sensitive genes overlap this 500kb duplication on chr17?"
11. "Is this CNV pathogenic based on ClinGen guidelines?"
12. "What is the population frequency of deletions in the DMD gene?"
13. "Interpret this SV VCF using ACMG/ClinGen criteria"
14. "Which genes in this region are haploinsufficient?"
15. "Compare SV burden between case and control cohorts"
16. "What known pathogenic CNVs overlap this region?"

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
| **SV/CNV Analysis (NEW)** | gnomAD SV population frequencies, DGVa/dbVar known SVs, ClinGen dosage sensitivity |
| **Clinical Interpretation (NEW)** | ACMG/ClinGen CNV pathogenicity classification using haploinsufficiency/triplosensitivity scores |
| **DataFrame** | Convert to pandas for advanced analytics |
| **Reporting** | Markdown reports with tables and statistics, SV clinical reports |

---

## Workflow Overview

```
Input VCF File (SNVs/indels or SVs)
    |
    v
Phase 1: Parse VCF
    |-- Pure Python parser (any VCF 4.x)
    |-- cyvcf2 parser (faster, C-based)
    |-- Extract: CHROM, POS, REF, ALT, QUAL, FILTER, INFO, FORMAT, samples
    |-- Extract per-sample: GT, VAF, depth
    |-- Extract annotations from INFO (ANN, CSQ, FUNCOTATION)
    |-- Detect variant class: SNV/indel vs SV/CNV
    |
    v
Phase 2: Classify Variants
    |-- Variant type: SNV, INS, DEL, MNV, COMPLEX, SV
    |-- Mutation type: missense, nonsense, synonymous, frameshift, splice, etc.
    |-- Impact: HIGH, MODERATE, LOW, MODIFIER
    |-- SV type: DEL, DUP, INV, BND, CNV (if structural variant)
    |
    v
Phase 3: Apply Filters
    |-- VAF range (min/max)
    |-- Read depth minimum
    |-- Quality threshold
    |-- PASS only
    |-- Variant/mutation type inclusion/exclusion
    |-- Consequence exclusion (intronic, intergenic)
    |-- Population frequency range
    |-- Chromosome selection
    |-- SV size range (for structural variants)
    |
    v
Phase 4: Compute Statistics
    |-- Variant type distribution
    |-- Mutation type distribution
    |-- Impact distribution
    |-- Chromosome distribution
    |-- Ti/Tv ratio (for SNVs)
    |-- Per-sample VAF/depth stats
    |-- Gene mutation counts
    |-- SV size distribution (for structural variants)
    |
    v
Phase 5: Annotate with ToolUniverse (optional)
    |-- MyVariant.info: ClinVar, dbSNP, gnomAD, CADD, SIFT, PolyPhen
    |-- dbSNP: Population frequencies, gene associations
    |-- gnomAD: Population allele frequencies
    |-- Ensembl VEP: Consequence prediction
    |
    v
Phase 6: Generate Report / Answer Question
    |-- Markdown report with tables
    |-- Direct answer to specific question
    |-- DataFrame for downstream analysis
    |
    v
Phase 7: Structural Variant & CNV Analysis (NEW - if SV/CNV detected)
    |-- Annotate with gnomAD SV population frequencies
    |-- Query DGVa/dbVar for known SVs (Ensembl)
    |-- Identify affected genes
    |-- Query ClinGen dosage sensitivity (HI/TS scores)
    |-- Classify pathogenicity (Pathogenic/Likely Pathogenic/VUS/Benign)
    |-- Generate SV clinical report with ACMG/ClinGen guidelines
```

---

## Phase Details

### Phase 1: VCF Parsing

**Objective**: Read VCF file and extract all variant records with per-sample data.

**Two parsers available**:
- **Pure Python**: Works everywhere, handles all VCF 4.x features
- **cyvcf2**: C-based, faster for large files, falls back to pure Python if unavailable

**Supported VCF Formats**:
- VCF 4.0, 4.1, 4.2
- Uncompressed (.vcf) and gzipped (.vcf.gz)
- Single-sample and multi-sample

**Per-variant data extracted**:
- Genomic coordinates (CHROM, POS, REF, ALT)
- Variant ID (rsID if available)
- Quality and filter status
- All INFO fields
- Per-sample: genotype (GT), allelic depth (AD), read depth (DP), variant allele frequency (AF/VAF)

**Annotation extraction from INFO**:
- SnpEff ANN field: consequence, impact, gene, transcript, protein change
- VEP CSQ field: consequence, impact, gene, transcript
- GATK Funcotator FUNCOTATION field
- Standard INFO keys: EFFECT, EFF, TYPE, GENE, CLNSIG

**VAF extraction methods** (tried in order):
1. AF/VAF/FREQ format field
2. AD (allelic depth): alt_depth / total_depth
3. AO/RO (FreeBayes): alt_obs / (alt_obs + ref_obs)
4. NR/NV: variant_reads / total_reads
5. INFO AF field (fallback for all samples)

### Phase 2: Variant Classification

**Variant type classification** (from REF/ALT):

| REF | ALT | Type |
|-----|-----|------|
| A | G | SNV |
| A | AT | INS |
| AT | A | DEL |
| AT | GC | MNV |
| AGC | TG | COMPLEX |

**Mutation type classification** (from consequence annotations):

| Consequence Term | Mutation Type | Impact |
|-----------------|---------------|--------|
| missense_variant | missense | MODERATE |
| stop_gained | nonsense | HIGH |
| frameshift_variant | frameshift | HIGH |
| synonymous_variant | synonymous | LOW |
| splice_acceptor_variant | splice_site | HIGH |
| splice_donor_variant | splice_site | HIGH |
| splice_region_variant | splice_region | LOW |
| inframe_insertion | inframe_insertion | MODERATE |
| inframe_deletion | inframe_deletion | MODERATE |
| intron_variant | intronic | MODIFIER |
| intergenic_variant | intergenic | MODIFIER |
| upstream_gene_variant | upstream | MODIFIER |
| downstream_gene_variant | downstream | MODIFIER |
| 5_prime_UTR_variant | UTR_5 | MODIFIER |
| 3_prime_UTR_variant | UTR_3 | MODIFIER |
| stop_lost | stop_lost | HIGH |
| start_lost | start_lost | HIGH |

**Also supports GATK Funcotator terms**: MISSENSE, NONSENSE, SILENT, SPLICE_SITE, etc.

### Phase 3: Filtering

**Available filter criteria**:

| Filter | Parameter | Description |
|--------|-----------|-------------|
| VAF minimum | `min_vaf` | Exclude variants with VAF below threshold |
| VAF maximum | `max_vaf` | Exclude variants with VAF above threshold |
| Depth minimum | `min_depth` | Exclude variants with depth below threshold |
| Quality minimum | `min_qual` | Exclude variants with QUAL below threshold |
| PASS only | `pass_only` | Only keep PASS/. variants |
| Variant type | `variant_types` | Include only specified types (SNV, INS, DEL, etc.) |
| Mutation type | `mutation_types` | Include only specified types (missense, nonsense, etc.) |
| Exclude consequences | `exclude_consequences` | Remove specified consequences |
| Include consequences | `include_consequences` | Keep only specified consequences |
| Population frequency | `max_population_freq` | Exclude common variants |
| Chromosome | `chromosomes` | Include only specified chromosomes |
| Sample | `sample` | Apply VAF/depth filters to specific sample |

**Specialized filters**:
- **Non-reference filter**: Remove variants where all samples are 0/0 (homozygous reference)
- **Intronic/intergenic filter**: Remove purely intronic, intergenic, upstream, and downstream variants (keeps splice_region)

### Phase 4: Statistics

**Computed statistics**:
- Variant type distribution (SNV, INS, DEL, MNV, COMPLEX)
- Mutation type distribution (missense, nonsense, synonymous, etc.)
- Impact distribution (HIGH, MODERATE, LOW, MODIFIER)
- Chromosome distribution
- Ti/Tv ratio (transitions / transversions)
- Per-sample VAF statistics (mean, median, min, max)
- Per-sample depth statistics
- Gene mutation counts
- Clinical significance distribution
- Filter status distribution

**Cross-tabulation**:
- VAF bins vs mutation types (for answering fraction questions)

### Phase 5: ToolUniverse Annotation

**MyVariant.info** (recommended, aggregates many sources):
- Query by rsID or HGVS notation
- Returns: ClinVar classification, dbSNP rsID, gnomAD allele frequency, CADD PHRED score, SIFT prediction, PolyPhen prediction, protein change

**dbSNP** (direct):
- Query by rsID
- Returns: Population frequencies (1000Genomes, ExAC, gnomAD, TOPMED, etc.), gene associations, clinical significance, HGVS notation

**gnomAD** (direct):
- Query by variant_id (format: "CHR-POS-REF-ALT")
- Returns: Basic variant metadata

**Ensembl VEP** (direct):
- Query by rsID or genomic region
- Returns: Consequence prediction, transcript impact

**Annotation workflow**:
1. For each variant (up to max_annotate limit)
2. Query MyVariant.info first (best coverage)
3. Optionally query dbSNP, gnomAD, VEP for additional data
4. Update variant records with annotation results

### Phase 6: Report Generation

**Markdown report sections**:
1. Summary Statistics (total variants, type counts, Ti/Tv)
2. Mutation Type Distribution (table with counts and percentages)
3. Impact Distribution
4. Chromosome Distribution
5. VAF Distribution (per-sample)
6. Clinical Significance
7. Top Mutated Genes
8. Variant Annotations (ClinVar-annotated variants)
9. Warnings and Errors

### Phase 7: Structural Variant & CNV Analysis (NEW)

**Objective**: Interpret the clinical significance of structural variants (deletions, duplications, inversions, translocations) and copy number variants using population frequencies and dosage sensitivity data.

**When to use**: When VCF contains SV calls (from Manta, Delly, LUMPY, etc.), BED file with CNV regions, or coordinate-based SV queries.

**Input formats**:
- VCF files with SVTYPE=DEL/DUP/INV/BND in INFO field
- BED files with CNV regions (chrom, start, end, type)
- Coordinate strings: "chr17:43044295-43070295"
- Gene-based queries: "What SVs affect [gene_symbol]?" (e.g., TP53, PTEN, ATM)

**SV/CNV Analysis Workflow**:

#### Step 1: Identify Structural Variants

Detect SVs from VCF by checking:
- SVTYPE field in INFO (DEL, DUP, INV, BND, CNV)
- Large indels (|len(REF) - len(ALT)| > 50bp)
- END coordinate in INFO field
- SVLEN field indicating SV size

Extract for each SV:
- Type (deletion, duplication, inversion, translocation)
- Coordinates (chromosome, start position, end position)
- Size (base pairs)
- Affected regions

#### Step 2: Annotate with Population Frequencies

Use gnomAD SV tools to determine if SV is common or rare:

```python
# Option A: Query by gene symbol
gnomad_sv = gnomad_get_sv_by_gene(gene_symbol="TP53")  # Or any gene symbol
# Returns: List of SVs affecting gene with population frequencies

# Option B: Query by genomic region
gnomad_sv = gnomad_get_sv_by_region(chrom="17", start=43044295, end=43070295)
# Returns: SVs overlapping region with AF, AC, AN

# Option C: Get detailed info for specific SV
sv_detail = gnomad_get_sv_detail(sv_id="DEL_chr17_24e4872b")
# Returns: Detailed SV info including filters, frequencies, size
```

**gnomAD SV response structure**:
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

**Frequency interpretation**:
- **AF > 0.01 (1%)**: Common benign variant
- **AF 0.001-0.01**: Low-frequency variant (uncertain)
- **AF < 0.001**: Rare variant (potentially pathogenic if affects critical gene)
- **Not in gnomAD**: Very rare or novel variant

#### Step 3: Query Known SVs from DGVa/dbVar

Use Ensembl tools to find previously reported SVs:

```python
# Query region for known SVs
ensembl_sv = ensembl_get_structural_variants(chrom="17", start=43044295, end=43070295, species="human")
# Returns: SVs from DGVa, dbVar with clinical annotations

# Get detailed info for specific SV
sv_info = ensembl_get_sv_detail(sv_id="esv3647486", species="human")
# Returns: Clinical significance, evidence, sample counts
```

**Ensembl SV response structure**:
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

#### Step 4: Identify Affected Genes

For each SV, determine which genes are impacted:

**Impact categories**:
- **Fully contained**: Gene entirely within SV boundaries (complete loss/gain)
- **Partially overlapping**: SV disrupts part of gene (potential disruption)
- **Regulatory disruption**: SV affects promoter/enhancer regions

Methods to identify genes:
1. From gnomAD SV response (`genes` field)
2. From Ensembl SV response
3. Query gene coordinates and compute overlap
4. Use gene annotation from VCF INFO field

#### Step 5: Query ClinGen Dosage Sensitivity

For each affected gene, determine if it's dosage-sensitive:

```python
# Option A: Query by gene symbol
clingen = ClinGen_dosage_by_gene(gene_symbol="BRCA1")
# Returns: Haploinsufficiency (HI) and triplosensitivity (TS) scores

# Option B: Query by region to find all dosage-sensitive genes
clingen_region = ClinGen_dosage_region_search(chromosome="17", start=43044295, end=43070295)
# Returns: All genes in region with dosage scores
```

**ClinGen response structure**:
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

**Dosage score interpretation**:

| Score | HI Meaning | TS Meaning | Clinical Impact |
|-------|-----------|------------|-----------------|
| **3** | Sufficient evidence | Sufficient evidence | **HIGH** - Established dosage sensitivity |
| **2** | Some evidence | Some evidence | **MODERATE** - Emerging evidence |
| **1** | Little evidence | Little evidence | **LOW** - Minimal evidence |
| **0** | No evidence | No evidence | **MINIMAL** - No known dosage effect |
| **30** | Gene associated with AD condition | - | **HIGH** (alternative scoring) |
| **40** | Dosage sensitivity unlikely | Dosage sensitivity unlikely | **MINIMAL** |

#### Step 6: Classify SV Pathogenicity

Combine evidence to classify SV using ACMG/ClinGen CNV guidelines:

**Pathogenic** (report as disease-causing):
- Deletion + HI score = 3 (sufficient evidence for haploinsufficiency)
- Duplication + TS score = 3 (sufficient evidence for triplosensitivity)
- gnomAD AF < 0.0001 (very rare)
- Gene is in ACMG Secondary Findings list
- Known pathogenic SV from ClinVar/dbVar with same breakpoints

**Likely Pathogenic**:
- Deletion + HI score = 2 (some evidence)
- Duplication + TS score = 2 (some evidence)
- gnomAD AF < 0.001
- Overlaps known pathogenic region but different breakpoints
- Disrupts critical functional domain

**Uncertain Significance (VUS)**:
- HI/TS score = 0 or 1 (no/little evidence)
- gnomAD AF 0.001-0.01 (conflicting frequency data)
- Affects gene but unclear clinical relevance
- Novel SV not in databases

**Likely Benign**:
- gnomAD AF > 0.01 (common in population)
- HI/TS score = 40 (dosage sensitivity unlikely)
- Does not affect any coding genes
- Matches known benign SV

**Benign**:
- gnomAD AF > 0.05 (very common)
- No overlap with any genes or regulatory regions
- Established benign variant in ClinVar

#### Step 7: Generate SV Clinical Report

Create comprehensive report with:

**Report sections**:
1. **SV Summary**
   - Type (deletion, duplication, etc.)
   - Coordinates (hg38/hg19)
   - Size (kb/Mb)
   - Population frequency (gnomAD AF)

2. **Affected Genes**
   - List of genes overlapping SV
   - Impact type (complete, partial, regulatory)
   - ClinGen dosage scores (HI/TS)
   - OMIM phenotypes

3. **Clinical Interpretation**
   - Pathogenicity classification
   - Evidence summary (dosage sensitivity + frequency + literature)
   - ACMG/ClinGen criteria met
   - Clinical recommendations

4. **Population Data**
   - gnomAD allele frequency
   - Allele count and number
   - Filter status (PASS/FAIL)

5. **Literature & Database Evidence**
   - ClinVar entries for region
   - DGVa/dbVar known SVs
   - OMIM disease associations
   - Published case reports

6. **Clinical Recommendations**
   - Confirmatory testing needed (if VUS)
   - Genetic counseling indicated (if pathogenic)
   - Family testing recommendations
   - Surveillance guidelines

**Example SV report**:

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

#### Step 8: Batch SV Analysis

For multiple SVs from whole-genome SV calling:

```python
# Example workflow for batch SV interpretation
def interpret_sv_batch(sv_vcf_path):
    results = []

    # Parse SV VCF
    svs = parse_sv_vcf(sv_vcf_path)

    for sv in svs:
        # Get population frequency
        gnomad = gnomad_get_sv_by_region(sv.chrom, sv.start, sv.end)

        # Identify affected genes
        genes = identify_affected_genes(sv)

        # Query dosage sensitivity for each gene
        dosage_results = []
        for gene in genes:
            clingen = ClinGen_dosage_by_gene(gene_symbol=gene)
            dosage_results.append(clingen)

        # Classify pathogenicity
        classification = classify_sv_pathogenicity(
            sv_type=sv.type,
            gnomad_af=gnomad['af'],
            dosage_scores=dosage_results
        )

        results.append({
            'sv_id': sv.id,
            'classification': classification,
            'genes': genes,
            'gnomad_af': gnomad['af'],
            'dosage_sensitive_genes': [
                g for g in dosage_results
                if g['haploinsufficiency_score'] >= 2 or g['triplosensitivity_score'] >= 2
            ]
        })

    return results
```

#### Key Considerations

**SV size thresholds**:
- **Large SVs** (>1 Mb): More likely to affect multiple genes, higher clinical impact
- **Exonic SVs** (>1 exon): Likely loss-of-function
- **Intronic SVs**: Usually benign unless affects splice sites
- **Regulatory SVs**: May affect gene expression

**SV type-specific interpretation**:
- **Deletions**: Check haploinsufficiency (HI) scores
- **Duplications**: Check triplosensitivity (TS) scores
- **Inversions**: May disrupt gene structure or regulatory elements
- **Translocations**: May create fusion genes or disrupt critical regions

**Caveats**:
- Breakpoint precision affects interpretation (use CIPOS/CIEND if available)
- Recurrent SV regions (e.g., 22q11.2) have established clinical significance
- De novo SVs more likely pathogenic than inherited
- Complex SVs require case-by-case interpretation

---

## Tool Parameter Reference

### ToolUniverse Tools Used

#### SNV/Indel Annotation Tools

| Tool | Parameters | Response Format |
|------|-----------|-----------------|
| `MyVariant_query_variants` | `query` (rsID or HGVS) | `{hits: [{_id, clinvar, dbsnp, cadd, gnomad_genome}]}` |
| `MyVariant_get_variant_annotation` | `variant_id` (HGVS) | Dict with annotation fields |
| `dbsnp_get_variant_by_rsid` | `rsid` | `{status, data: {rsid, chromosome, allele_frequencies, clinical_significance}}` |
| `gnomad_get_variant` | `variant_id` (CHR-POS-REF-ALT) | `{status, data: {data: {variant: {variant_id, chrom, pos}}}}` |
| `EnsemblVEP_annotate_rsid` | `variant_id` (rsID) | Variable: list or `{data, metadata}` or `{error}` |
| `ensembl_vep_region` | `region`, `species` | `{status, data}` |

#### Structural Variant & CNV Tools (NEW)

| Tool | Parameters | Response Format |
|------|-----------|-----------------|
| `gnomad_get_sv_by_gene` | `gene_symbol` | `{data: {structural_variants: [{variant_id, chrom, pos, end, sv_type, size, af, ac, an, filters, genes}]}}` |
| `gnomad_get_sv_by_region` | `chrom`, `start`, `end` | `{data: {structural_variants: [...]}}` |
| `gnomad_get_sv_detail` | `sv_id` | `{data: {variant_id, chrom, pos, end, sv_type, size, af, ac, an, filters, quality_metrics}}` |
| `ensembl_get_structural_variants` | `chrom`, `start`, `end`, `species` | `{data: [{id, var_class, clinical_significance, evidence, study, sample_count}]}` |
| `ensembl_get_sv_detail` | `sv_id`, `species` | `{data: {id, var_class, clinical_significance, source, study}}` |
| `ClinGen_dosage_by_gene` | `gene_symbol` | `{data: {gene_symbol, haploinsufficiency_score, triplosensitivity_score, dosage_sensitivity_disease, pli_score, acmg_secondary_findings}}` |
| `ClinGen_dosage_region_search` | `chromosome`, `start`, `end` | `{data: {genes: [{gene_symbol, haploinsufficiency_score, triplosensitivity_score}]}}` |

### Key Response Structure Notes

- **MyVariant_query_variants**: Most reliable for batch annotation. Aggregates ClinVar, dbSNP, gnomAD, CADD in one call
- **MyVariant ClinVar RCV**: Can be list or dict; always handle both
- **gnomAD AF**: Nested under `af.af` (overall) and `af.af_afr`, `af.af_nfe`, etc. (ancestry-specific)
- **CADD**: `cadd.phred` for PHRED-scaled score (>=20 = top 1% deleterious)
- **EnsemblVEP**: Variable response format; handle list, dict, and error cases

---

## Answering BixBench Questions

### Pattern 1: VAF + Mutation Type Fraction

**Question**: "What fraction of variants with VAF < X are annotated as Y mutations?"

**Workflow**:
1. Parse VCF
2. Filter variants with VAF < X (using first sample or specified sample)
3. Count variants matching mutation type Y
4. Return fraction = matching / total_below_vaf

### Pattern 2: Cohort Comparison

**Question**: "What is the difference in mutation frequency between cohorts?"

**Workflow**:
1. Parse each cohort VCF
2. Count mutation type frequency in each cohort
3. Compute difference

### Pattern 3: Filter and Count

**Question**: "After filtering X, how many Y remain?"

**Workflow**:
1. Parse VCF
2. Apply filters (non-reference, intronic/intergenic, etc.)
3. Count remaining variants

### Pattern 4: Distribution Questions

**Question**: "What is the distribution of X?"

**Workflow**:
1. Parse VCF
2. Compute statistics
3. Return relevant distribution

### Pattern 5: Annotation Questions

**Question**: "How many variants have clinical significance?"

**Workflow**:
1. Parse VCF (extract CLNSIG from INFO if present)
2. Optionally annotate with MyVariant.info
3. Count variants with clinical_significance set

---

## Fallback Strategies

| Primary | Fallback | Use When |
|---------|----------|----------|
| cyvcf2 parser | Pure Python parser | cyvcf2 not installed |
| SnpEff ANN | VEP CSQ | Different annotation pipeline |
| VEP CSQ | GATK FUNCOTATION | Different annotation pipeline |
| AF format field | AD-computed VAF | No AF field in FORMAT |
| MyVariant.info | dbSNP + gnomAD (direct) | MyVariant API unavailable |
| Per-sample VAF | INFO AF | No per-sample data |

---

## Limitations

- **VCF annotation required for mutation classification**: If VCF has no ANN/CSQ/FUNCOTATION in INFO, mutation types will be "unknown" until ToolUniverse annotation is applied
- **Multi-allelic variants**: Parser takes first ALT allele for type classification
- **ToolUniverse annotation rate**: API-based, limited to ~100 variants per batch by default to respect rate limits
- **gnomAD tool**: Returns basic metadata only (not full allele frequencies); use MyVariant.info for gnomAD AF
- **VEP annotation**: EnsemblVEP tools may return errors for some variants; MyVariant.info is more reliable
- **Large VCFs**: Pure Python parser streams line-by-line; cyvcf2 is recommended for files with >100K variants

---

## Quantified Minimums

| Section | Requirement |
|---------|-------------|
| VCF parsing | All variants parsed with coordinates and alleles |
| VAF extraction | At least one VAF extraction method attempted |
| Mutation classification | All annotated variants classified |
| Statistics | Ti/Tv ratio, type distribution, per-sample VAF stats |
| Report | All 7+ sections present in markdown report |
| Annotation (if enabled) | Up to 100 variants annotated via MyVariant.info |

---

## Common Use Patterns

### Pattern 1: Quick VCF Summary
Parse VCF, compute statistics, generate report.

### Pattern 2: Filtered Analysis
Parse VCF, apply multi-criteria filter, compute statistics on filtered set.

### Pattern 3: Annotated Report
Parse VCF, annotate top variants with ClinVar/gnomAD/CADD, generate clinical report.

### Pattern 4: BixBench Question Answering
Parse VCF, apply specific filters, compute targeted statistics to answer precise questions.

### Pattern 5: Cohort Comparison
Parse multiple VCFs, compare mutation frequencies across cohorts.
