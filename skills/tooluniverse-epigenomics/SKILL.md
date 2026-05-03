---
name: tooluniverse-epigenomics
description: Production-ready genomics and epigenomics data processing for BixBench questions. Handles methylation array analysis (CpG filtering, differential methylation, age-related CpG detection, chromosome-level density), ChIP-seq peak analysis (peak calling, motif enrichment, coverage stats), ATAC-seq chromatin accessibility, multi-omics integration (expression + methylation correlation), and genome-wide statistics. Pure Python computation (pandas, scipy, numpy, pysam, statsmodels) plus ToolUniverse annotation tools (Ensembl, ENCODE, SCREEN, JASPAR, ReMap, RegulomeDB, ChIPAtlas). Supports BED, BigWig, methylation beta-value matrices, Illumina manifest files, and multi-sample clinical data. Use when processing methylation data, ChIP-seq peaks, ATAC-seq signals, or answering questions about CpG sites, differential methylation, chromatin accessibility, histone marks, or epigenomic statistics.
---

# Genomics and Epigenomics Data Processing

Production-ready skill combining Python computation (pandas, scipy, numpy, pysam, statsmodels) with ToolUniverse annotation tools for epigenomics analysis.

## LOOK UP, DON'T GUESS
When uncertain about any scientific fact, SEARCH databases first.

## When to Use

Methylation data, ChIP-seq peaks, ATAC-seq, multi-omics integration, genome-wide epigenomic statistics. Keywords: methylation, CpG, ChIP-seq, ATAC-seq, histone, chromatin, epigenetic.

**NOT for**: RNA-seq DEG, variant calling, gene enrichment, protein structure.

---

## Key Principles

1. **Data-first** - Load/inspect before analysis
2. **Question-driven** - Extract specific numeric answer
3. **Coordinate system awareness** - Track genome build (hg19/hg38/mm10), chr prefix
4. **Statistical rigor** - FDR correction, effect size filtering
5. **CpG identification** - Parse Illumina probe IDs, genomic coordinates

---

## Workflow

### Phase 0: Question Parsing
Identify data files, specific statistic, thresholds, genome build. Categorize by keywords.
See `ANALYSIS_PROCEDURES.md` for decision tree.

### Phase 1: Methylation Processing
- Load beta/M-value matrix (CSV/TSV/parquet/HDF5)
- Filter by variance, missing rate, probe type, chromosome, CpG island relation
- Differential methylation: T-test/Wilcoxon between groups + FDR
- Age-related CpG: Pearson/Spearman correlation + FDR
- Chromosome density: CpG count / chromosome length

### Phase 2: ChIP-seq Peak Analysis
- Load BED/narrowPeak/broadPeak, normalize chromosomes
- Peak stats, annotation to genes, overlap analysis (Jaccard)

### Phase 3: ATAC-seq
- NFR detection (<150bp peaks), region classification

### Phase 4: Multi-Omics Integration
- Methylation-expression correlation per probe-gene (Pearson/Spearman + FDR)
- ChIP-seq + expression: promoter peaks vs expression levels

### Phase 5: Clinical Data
- Missing data analysis across modalities, complete case identification

### Phase 6: ToolUniverse Annotation

**ENCODE tools**:
- `ENCODE_search_rnaseq_experiments`: `assay_type` ("total RNA-seq" default; fall back to "polyA plus RNA-seq"), `biosample`, `limit`
- `ENCODE_search_histone_experiments`: `target` (e.g., "H3K27ac"), `cell_type`/`tissue`/`biosample`, `limit`

**GEO tools**: `GEO_search_rnaseq_datasets`, `GEO_search_atacseq_datasets` -- both accept `limit` or `max_results`

**GTEx tools**:
- `GTEx_get_median_gene_expression`: `gene_symbol` (NOT Ensembl ID)
- `GTEx_query_eqtl`: `gene_symbol`, `tissue_id` (case-sensitive exact, e.g., `"Whole_Blood"`)

**Other**: `ensembl_lookup_gene` (requires `species='homo_sapiens'`), `ensembl_get_regulatory_features` (NO "chr" prefix), `SCREEN_get_regulatory_elements`, `ChIPAtlas_*` (requires `operation` param), `SRA_search_experiments` (library_strategy: "ChIP-Seq"/"Bisulfite-Seq"/"ATAC-seq")

### Phase 7: Genome-Wide Statistics
Global mean/median beta, probe variance, chromosome density, DMP counts.

See `CODE_REFERENCE.md` for full implementations.

---

## Common Patterns

| Pattern | Key Steps |
|---------|-----------|
| Differential methylation | Filter probes → groups → t-test → FDR → threshold |
| Age-related CpG density | Correlate with age → FDR → map to chr → density ratio |
| Multi-omics missing data | Extract IDs → intersect → check NaN → complete case count |
| ChIP-seq annotation | Load peaks → annotate genes → classify regions |
| Methylation-expression | Align samples → correlate → FDR → anti-correlations |

---

## GTEx Tissue IDs

Whole_Blood, Liver, Lung, Breast_Mammary_Tissue, Brain_Cortex, Heart_Left_Ventricle, Kidney_Cortex, Thyroid, Adipose_Subcutaneous, Muscle_Skeletal

---

## Evidence Grading

| Grade | Criteria |
|-------|----------|
| **Strong** | padj < 0.01 AND abs(delta-beta) >= 0.2, replicated |
| **Moderate** | padj < 0.05 AND abs(delta-beta) >= 0.1 |
| **Weak** | padj < 0.05 but delta-beta < 0.1 |
| **Insufficient** | padj >= 0.05 or no replication |

Delta-beta >= 0.2 = strong effect. ChIP-seq: q < 0.01, FE >= 2 for confidence. ATAC-seq NFR < 150bp = active regulatory. Always apply BH FDR. Verify genome build consistency.

---

## Limitations

- No pybedtools/pyBigWig: pure Python intervals
- Illumina-centric (450K/EPIC); uses t-test/Wilcoxon (not limma)
- No peak calling (assumes pre-called)
- API rate limits: ~20 genes per batch

## Reference Files

`CODE_REFERENCE.md`, `TOOLS_REFERENCE.md`, `ANALYSIS_PROCEDURES.md`, `QUICK_START.md`
