---
name: tooluniverse-epigenomics
description: Production-ready genomics and epigenomics data processing for BixBench questions. Handles methylation array analysis (CpG filtering, differential methylation, age-related CpG detection, chromosome-level density), ChIP-seq peak analysis (peak calling, motif enrichment, coverage stats), ATAC-seq chromatin accessibility, multi-omics integration (expression + methylation correlation), and genome-wide statistics. Pure Python computation (pandas, scipy, numpy, pysam, statsmodels) plus ToolUniverse annotation tools (Ensembl, ENCODE, SCREEN, JASPAR, ReMap, RegulomeDB, ChIPAtlas). Supports BED, BigWig, methylation beta-value matrices, Illumina manifest files, and multi-sample clinical data. Use when processing methylation data, ChIP-seq peaks, ATAC-seq signals, or answering questions about CpG sites, differential methylation, chromatin accessibility, histone marks, or epigenomic statistics.
---

# Genomics and Epigenomics Data Processing

Production-ready computational skill for processing and analyzing epigenomics data. Combines local Python computation (pandas, scipy, numpy, pysam, statsmodels) with ToolUniverse annotation tools for regulatory context. Designed to solve BixBench-style questions about methylation, ChIP-seq, ATAC-seq, and multi-omics integration.

## When to Use This Skill

**Triggers**:
- User provides methylation data (beta-value matrices, Illumina arrays) and asks about CpG sites
- Questions about differential methylation analysis
- Age-related CpG detection or epigenetic clock questions
- Chromosome-level methylation density or statistics
- ChIP-seq peak files (BED format) with analysis questions
- ATAC-seq chromatin accessibility questions
- Multi-omics integration (expression + methylation, expression + ChIP-seq)
- Genome-wide epigenomic statistics
- Questions mentioning "methylation", "CpG", "ChIP-seq", "ATAC-seq", "histone", "chromatin", "epigenetic"
- Questions about missing data across clinical/genomic/epigenomic modalities
- Regulatory element annotation for processed epigenomic data

**Example Questions**:
1. "How many patients have no missing data for vital status, gene expression, and methylation data?"
2. "What is the ratio of filtered age-related CpG density between chromosomes?"
3. "What is the genome-wide average chromosomal density of unique age-related CpGs per base pair?"
4. "How many CpG sites show significant differential methylation (padj < 0.05)?"
5. "What is the Pearson correlation between methylation and expression for gene X?"
6. "How many ChIP-seq peaks overlap with promoter regions?"
7. "What fraction of ATAC-seq peaks are in enhancer regions?"
8. "Which chromosome has the highest density of hypermethylated CpGs?"
9. "Filter CpG sites by variance > threshold and map to nearest genes"
10. "What is the average beta value difference between tumor and normal for chromosome 17?"

**NOT for** (use other skills instead):
- Gene regulation lookup without data files -> Use existing epigenomics annotation pattern
- RNA-seq differential expression -> Use `tooluniverse-rnaseq-deseq2`
- Variant calling/annotation from VCF -> Use `tooluniverse-variant-analysis`
- Gene enrichment analysis -> Use `tooluniverse-gene-enrichment`
- Protein structure analysis -> Use `tooluniverse-protein-structure-retrieval`

---

## Required Python Packages

```python
# Core (MUST be available)
import pandas as pd
import numpy as np
from scipy import stats
import statsmodels.stats.multitest as mt

# Optional but useful
import pysam      # BAM/CRAM file access
import gseapy     # Enrichment of genes from methylation analysis

# ToolUniverse (for annotation)
from tooluniverse import ToolUniverse
```

---

## Key Principles

1. **Data-first approach** - Load and inspect data files BEFORE any analysis
2. **Question-driven** - Parse what the user is actually asking and extract the specific numeric answer
3. **File format detection** - Automatically detect methylation arrays, BED files, BigWig, clinical data
4. **Coordinate system awareness** - Track genome build (hg19, hg38, mm10), handle chr prefix differences
5. **Statistical rigor** - Proper multiple testing correction, effect size filtering, sample size awareness
6. **Missing data handling** - Explicitly report and handle NaN/missing values
7. **Chromosome normalization** - Always normalize chromosome names (chr1 vs 1, chrX vs X)
8. **CpG site identification** - Parse Illumina probe IDs (cg/ch probes), genomic coordinates
9. **Report-first** - Create output file first, populate progressively
10. **English-first queries** - Use English in all tool calls

---

## Workflow Overview

### Phase 0: Question Parsing and Data Discovery

Before writing any code, parse the question to identify:
- What data files are available (methylation, ChIP-seq, ATAC-seq, clinical, expression, manifest)
- What specific statistic or answer is being asked for
- What thresholds apply (significance, effect size, variance, chromosome filters)
- What genome build to use

Categorize files by scanning for keywords: methyl/beta/cpg/illumina, chip/peak/narrowpeak, atac/accessibility, clinical/patient/sample, express/rnaseq/fpkm, manifest/annotation/probe.

See `ANALYSIS_PROCEDURES.md` for the full decision tree and parameter extraction table.

### Phase 1: Methylation Data Processing

Core functions for methylation analysis:
- **Load methylation data** - Supports CSV, TSV, parquet, HDF5; auto-detects beta vs M-values
- **Load probe manifest** - Illumina 450K/EPIC manifest with chromosome, position, gene annotation
- **CpG filtering** - Filter by variance, missing rate, probe type (cg/ch), chromosome, CpG island relation, gene group
- **Differential methylation** - T-test/Wilcoxon/KS between groups with FDR correction; identify DMPs (hyper/hypo)
- **Age-related CpG analysis** - Pearson/Spearman correlation of probes with age, FDR correction
- **Chromosome-level density** - CpG count per chromosome divided by chromosome length; density ratios; genome-wide average

See `CODE_REFERENCE.md` Phase 1 for full function implementations.

### Phase 2: ChIP-seq Peak Analysis

- **Load BED/narrowPeak/broadPeak** - Auto-detect format, normalize chromosomes
- **Peak statistics** - Count, length distribution, signal values, q-values
- **Peak annotation** - Map peaks to nearest gene, classify as promoter/gene_body/proximal/distal
- **Peak overlap** - Pure Python interval intersection between two BED files; Jaccard similarity

See `CODE_REFERENCE.md` Phase 2 for full function implementations.

### Phase 3: ATAC-seq Analysis

- **Load ATAC peaks** - Wrapper around BED loader for narrowPeak format
- **ATAC-specific stats** - Nucleosome-free region (NFR) detection (<150bp peaks), region classification
- **Chromatin accessibility by region** - Distribution of open chromatin across promoter/enhancer/intergenic

See `CODE_REFERENCE.md` Phase 3 for full function implementations.

### Phase 4: Multi-Omics Integration

- **Methylation-expression correlation** - Align samples, compute per-probe-gene Pearson/Spearman with FDR
- **ChIP-seq + expression** - Find genes with promoter peaks and compare expression levels

See `CODE_REFERENCE.md` Phase 4 for full function implementations.

### Phase 5: Clinical Data Integration

- **Missing data analysis** - Count samples present across clinical, expression, and methylation modalities
- **Complete case identification** - Find intersection of samples with non-missing values for specified variables

See `CODE_REFERENCE.md` Phase 5 for full function implementations.

### Phase 6: ToolUniverse Annotation

Use ToolUniverse tools to add biological context after computational analysis:
- **Gene annotation** - Ensembl lookup for coordinates, biotype, cross-references
- **Regulatory elements** - SCREEN cCREs (enhancers, promoters, insulators)
- **ChIPAtlas** - Query available ChIP-seq experiments by antigen/cell type
- **Ensembl regulatory features** - Annotate genomic regions with regulatory overlaps

#### ENCODE RNA-seq and ATAC-seq datasets

**ENCODE_search_rnaseq_experiments**: `assay_type` (string, default "total RNA-seq"), `biosample` (string/null, e.g. "liver"), `limit` (int).
Available assay_type values: `"total RNA-seq"`, `"polyA plus RNA-seq"`, `"small RNA-seq"`, `"microRNA-seq"`.
- NOTE: If `total RNA-seq` returns 0 results for a biosample, fall back to `polyA plus RNA-seq`.

```json
{"assay_type": "total RNA-seq", "biosample": "K562", "limit": 5}
// Fallback if 0 results:
{"assay_type": "polyA plus RNA-seq", "biosample": "K562", "limit": 5}
```

**ENCODE_search_histone_experiments**: `target` (string, histone mark name e.g. "H3K27ac"), `cell_type` (string/null), `tissue` (alias for cell_type), `biosample` (alias), `limit` (int).
Returns `{status, data: {total, experiments: [{accession, histone_mark, biosample_summary, status, lab}]}}`.

#### GEO RNA-seq and ATAC-seq datasets

**GEO_search_rnaseq_datasets**: `query` (string, free-text keyword), `organism` (string, default "Homo sapiens"), `limit` (int, also `max_results` accepted).
Returns GEO Series accessions (GSExxxxxx) with titles, summaries, sample counts.

**GEO_search_atacseq_datasets**: `query` (string), `organism` (string, default "Homo sapiens"), `limit` (int, also `max_results` accepted).
Returns GEO ATAC-seq datasets matching the query.

NOTE: Both `limit` and `max_results` are accepted as parameter names for GEO tools.

```json
// GEO RNA-seq for breast cancer
{"query": "breast cancer", "limit": 5}

// GEO ATAC-seq for T cells
{"query": "T cells", "limit": 5}
```

#### GTEx expression and eQTL tools

**GTEx_get_median_gene_expression**: `gene_symbol` (string). Returns median TPM per tissue across all GTEx tissues.

**GTEx_get_expression_summary**: `gene_symbol` (string). Returns clustered median expression.
- NOTE: Use `gene_symbol` (e.g. "PCSK9"), NOT a versioned Ensembl ID.

**GTEx_query_eqtl**: `gene_symbol` (string), `tissue_id` (string, exact tissueSiteDetailId), `page` (int, 1-indexed), `size` (int, default 10).
- CRITICAL: `tissue_id` is case-sensitive and must be exact (e.g. `"Whole_Blood"`, not `"whole blood"`).
- Returns empty array if no significant eQTLs exist for that gene+tissue pair.

```json
// eQTLs for PCSK9 in Whole Blood
{"gene_symbol": "PCSK9", "tissue_id": "Whole_Blood"}

// Median expression across all tissues
{"gene_symbol": "BRCA1"}
```

See `CODE_REFERENCE.md` Phase 6 and `TOOLS_REFERENCE.md` for parameters.

### Phase 7: Genome-Wide Statistics

- **Comprehensive methylation stats** - Global mean/median beta, probe variance, chromosome density
- **Differential methylation summary** - Count significant, hyper/hypo split, effect sizes

See `CODE_REFERENCE.md` Phase 7 for full function implementations.

---

## Common Analysis Patterns

| Pattern | Input | Key Steps | Output |
|---------|-------|-----------|--------|
| Differential methylation | Beta matrix + clinical | Filter probes -> define groups -> t-test -> FDR -> threshold | Count of significant DMPs |
| Age-related CpG density | Beta matrix + manifest + ages | Correlate with age -> FDR -> map to chr -> density per chr | Density ratio between chromosomes |
| Multi-omics missing data | Clinical + expression + methylation | Extract sample IDs -> intersect -> check NaN | Complete case count |
| ChIP-seq peak annotation | BED/narrowPeak + gene annotation | Load peaks -> annotate to genes -> classify regions | Fraction in promoters |
| Methylation-expression | Beta matrix + expression + probe-gene map | Align samples -> correlate -> FDR | Significant anti-correlations |

See `ANALYSIS_PROCEDURES.md` for detailed step-by-step flows and edge case handling.

---

## Key Functions Reference

| Function | Purpose | Input | Output |
|----------|---------|-------|--------|
| `load_methylation_data()` | Load beta/M-value matrix | file path | DataFrame |
| `detect_methylation_type()` | Detect beta vs M-values | DataFrame | 'beta' or 'mvalue' |
| `filter_cpg_probes()` | Filter probes by criteria | DataFrame + filters | filtered DataFrame |
| `differential_methylation()` | DM analysis between groups | beta + samples | DataFrame with padj |
| `identify_age_related_cpgs()` | Age-correlated CpGs | beta + ages | DataFrame with padj |
| `chromosome_cpg_density()` | CpG density per chromosome | probes + manifest | density DataFrame |
| `genome_wide_average_density()` | Overall genome density | density DataFrame | float |
| `chromosome_density_ratio()` | Ratio between chromosomes | density + chr names | float |
| `load_bed_file()` | Load BED/narrowPeak | file path | DataFrame |
| `peak_statistics()` | Basic peak stats | BED DataFrame | dict |
| `annotate_peaks_to_genes()` | Annotate peaks to genes | peaks + genes | annotated DataFrame |
| `find_overlaps()` | Peak overlap analysis | two BED DataFrames | overlap DataFrame |
| `missing_data_analysis()` | Cross-modality completeness | multiple DataFrames | dict |
| `correlate_methylation_expression()` | Meth-expression correlation | beta + expression | correlation DataFrame |

---

## ToolUniverse Tools Used

### Regulatory Annotation Tools
- `ensembl_lookup_gene` - Gene coordinates, biotype (REQUIRES `species='homo_sapiens'`)
- `ensembl_get_regulatory_features` - Regulatory features by region (NO "chr" prefix in region)
- `ensembl_get_overlap_features` - Gene/transcript overlap data
- `SCREEN_get_regulatory_elements` - cCREs: enhancers, promoters, insulators
- `ReMap_get_transcription_factor_binding` - TF binding sites
- `RegulomeDB_query_variant` - Variant regulatory score
- `jaspar_search_matrices` - TF binding matrices
- `ENCODE_search_experiments` - Experiment metadata (assay_title must be "TF ChIP-seq" not "ChIP-seq")
- `ENCODE_search_rnaseq_experiments` - RNA-seq experiments (assay_type: "total RNA-seq" or "polyA plus RNA-seq")
- `ENCODE_search_histone_experiments` - Histone ChIP-seq experiments by mark and cell type
- `GEO_search_rnaseq_datasets` - GEO RNA-seq datasets (limit or max_results accepted)
- `GEO_search_atacseq_datasets` - GEO ATAC-seq datasets (limit or max_results accepted)
- `GTEx_get_median_gene_expression` - Median TPM across GTEx tissues
- `GTEx_get_expression_summary` - Clustered expression summary
- `GTEx_query_eqtl` - eQTL associations (tissue_id must be exact, e.g. 'Whole_Blood')
- `ChIPAtlas_get_experiments` - ChIP-seq experiments (REQUIRES `operation` param)
- `ChIPAtlas_search_datasets` - Dataset search (REQUIRES `operation` param)
- `ChIPAtlas_enrichment_analysis` - Enrichment from BED/motifs/genes
- `ChIPAtlas_get_peak_data` - Peak data download (REQUIRES `operation` param)
- `FourDN_search_data` - Chromatin conformation data (REQUIRES `operation` param)

### Gene Annotation Tools
- `MyGene_query_genes` - Gene query
- `MyGene_batch_query` - Batch gene query
- `HGNC_fetch_gene_by_symbol` - Gene symbol, aliases, IDs
- `GO_get_annotations_for_gene` - GO annotations

### Sequencing Data Retrieval Tools (SRA)
- `SRA_search_experiments` - Search NCBI SRA for raw sequencing experiments by keyword, organism, library strategy, or platform
- `SRA_get_experiment` - Get detailed metadata for a specific SRA experiment by accession

Use SRA tools to find raw epigenomics sequencing data (ChIP-seq, Bisulfite-Seq, ATAC-seq) for cross-study comparison or to identify available datasets for a tissue/condition.

| Tool | Key Parameters | Returns |
|------|----------------|---------|
| `SRA_search_experiments` | `query` (free text), `organism` (e.g. "Homo sapiens"), `library_strategy` ("ChIP-Seq", "Bisulfite-Seq", "ATAC-seq"), `platform` ("ILLUMINA"), `limit` | `{data: {total, returned, experiments: [{uid, title, organism, library_strategy, experiment_accession, study_accession, bioproject}]}}` |
| `SRA_get_experiment` | `accession` (SRX/ERX/DRX/SRP/ERP/DRP) | Full experiment metadata with runs |

```python
# Example: Find ATAC-seq experiments for human liver
result = tu.tools.SRA_search_experiments(
    query="liver", organism="Homo sapiens",
    library_strategy="ATAC-seq", limit=5
)

# Example: Find Bisulfite-Seq for breast cancer
result = tu.tools.SRA_search_experiments(
    query="breast cancer", library_strategy="Bisulfite-Seq", limit=5
)
```

See `TOOLS_REFERENCE.md` for full parameter details and return schemas.

---

## Data Format Notes

- **Methylation data**: Probes (rows) x samples (columns), beta values 0-1
- **BED files**: Tab-separated, 0-based half-open coordinates
- **narrowPeak**: 10-column BED extension with signalValue, pValue, qValue, peak
- **Illumina manifests**: Probe ID, chromosome, position, gene annotation
- **Clinical data**: Patient/sample-centric with clinical variables as columns

## Genome Builds Supported

| Build | Species | Autosomes | Sex Chromosomes |
|-------|---------|-----------|-----------------|
| hg38 (GRCh38) | Human | chr1-chr22 | chrX, chrY |
| hg19 (GRCh37) | Human | chr1-chr22 | chrX, chrY |
| mm10 (GRCm38) | Mouse | chr1-chr19 | chrX, chrY |

## GTEx Tissue Site Detail IDs (common)

| Tissue | tissueSiteDetailId |
|--------|-------------------|
| Whole Blood | Whole_Blood |
| Liver | Liver |
| Lung | Lung |
| Breast | Breast_Mammary_Tissue |
| Brain Cortex | Brain_Cortex |
| Heart Left Ventricle | Heart_Left_Ventricle |
| Kidney Cortex | Kidney_Cortex |
| Thyroid | Thyroid |
| Adipose Subcutaneous | Adipose_Subcutaneous |
| Muscle Skeletal | Muscle_Skeletal |

## Reasoning Framework for Result Interpretation

### Evidence Grading

| Grade | Criteria | Example |
|-------|----------|---------|
| **Strong** | padj < 0.01 AND abs(delta-beta) >= 0.2, replicated across cohorts | DMP with padj = 1e-8, delta-beta = 0.35 in two independent datasets |
| **Moderate** | padj < 0.05 AND abs(delta-beta) >= 0.1 | DMP with padj = 0.02, delta-beta = 0.15 |
| **Weak** | padj < 0.05 but abs(delta-beta) < 0.1 | Statistically significant but biologically marginal change |
| **Insufficient** | padj >= 0.05 or no biological replication | Sub-threshold after FDR correction |

### Interpretation Guidance

- **Methylation delta-beta cutoffs**: A delta-beta (mean beta difference between groups) of 0.1 (10%) is a common minimum threshold for biological relevance on 450K/EPIC arrays. Delta-beta >= 0.2 is considered a strong effect. Statistical significance alone (small p-value) without meaningful delta-beta often reflects technical noise in large-sample studies.
- **ChIP-seq peak quality**: Assess peaks by q-value (< 0.01 for high confidence), signal-to-noise ratio, and IDR (irreproducible discovery rate < 0.05 across replicates). Peaks with FE (fold enrichment) < 2 should be treated cautiously. Broad marks (H3K27me3, H3K36me3) have wider peaks than sharp marks (H3K4me3, CTCF).
- **ATAC-seq accessibility interpretation**: Nucleosome-free regions (NFR, < 150 bp fragments) indicate active regulatory elements. Peaks at promoters (TSS +/- 2kb) suggest active transcription. Distal peaks often mark enhancers. Peak width and fragment size distribution are quality indicators -- a clear NFR peak with nucleosomal periodicity indicates good library quality.
- **Multiple testing**: Always apply FDR correction (Benjamini-Hochberg) when testing thousands of CpG sites or peaks. Report both nominal and adjusted p-values.
- **Genome build consistency**: Verify all data uses the same build (hg19 vs hg38) before overlapping methylation sites with ChIP-seq peaks or regulatory annotations.

### Synthesis Questions

1. Do differentially methylated positions (DMPs) meeting both statistical and effect-size thresholds cluster in regulatory regions (promoters, enhancers), or are they scattered across the genome?
2. For ChIP-seq data, do peaks replicate across biological replicates (IDR analysis), and do they overlap with expected genomic features for the histone mark (e.g., H3K4me3 at promoters)?
3. When integrating methylation and accessibility data, do hypomethylated regions correspond to ATAC-seq open chromatin peaks, supporting a consistent regulatory model?
4. Are age-related or condition-related CpG changes enriched in known epigenetic clock CpGs, or do they represent novel associations?
5. Does the observed methylation change at a locus correlate with expression change of the nearest gene, or is the CpG in a region with no clear regulatory function?

---

## Limitations

- No native pybedtools: uses pure Python interval operations
- No native pyBigWig: cannot read BigWig files directly without package
- No R bridge: does not use methylKit, ChIPseeker, or DiffBind
- Illumina-centric: methylation functions designed for 450K/EPIC arrays
- Uses t-test/Wilcoxon for differential methylation (not limma/bumphunter)
- No peak calling: assumes peaks are pre-called
- API rate limits: ToolUniverse annotation limited to ~20 genes per batch

---

## Reference Files

- `CODE_REFERENCE.md` - Full Python function implementations for all phases
- `TOOLS_REFERENCE.md` - ToolUniverse tool parameter details and return schemas
- `ANALYSIS_PROCEDURES.md` - Decision trees, step-by-step analysis patterns, edge cases, fallback strategies
- `QUICK_START.md` - Quick start examples for common analysis types
