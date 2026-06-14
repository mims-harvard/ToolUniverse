# Analysis Procedures Reference

Detailed decision trees, step-by-step analysis patterns, edge cases, and fallback strategies for the epigenomics skill.

---

## Question Parameter Extraction

Extract these from the user's question before starting analysis:

| Parameter | Default | Example Question Text |
|-----------|---------|----------------------|
| **Significance threshold** | 0.05 | "padj < 0.05", "FDR < 0.01" |
| **Beta difference threshold** | 0 | "|delta_beta| > 0.2", "mean difference > 0.1" |
| **Variance filter** | None | "variance > 0.01", "top 5000 most variable" |
| **Chromosome filter** | All | "chromosome 17", "autosomes only" |
| **Genome build** | hg38 | "hg19", "GRCh37", "mm10" |
| **CpG type filter** | All | "cg probes only", "exclude ch probes" |
| **Region filter** | None | "promoter", "gene body", "intergenic" |
| **Missing data handling** | Report | "complete cases", "no missing data" |
| **Specific comparison** | Infer | "tumor vs normal", "old vs young" |
| **Specific statistic** | Infer | "density", "ratio", "count", "average" |

---

## Decision Tree

```
Q: What type of epigenomics data?
  METHYLATION -> Phase 1 (Methylation Processing)
  CHIP-SEQ    -> Phase 2 (ChIP-seq Processing)
  ATAC-SEQ    -> Phase 3 (ATAC-seq Processing)
  MULTI-OMICS -> Phase 4 (Integration)
  CLINICAL    -> Phase 5 (Clinical Integration)
  ANNOTATION  -> Phase 6 (ToolUniverse Annotation)

Q: Is this a genome-wide statistics question?
  YES -> Focus on chromosome-level aggregation (Phase 7)
  NO  -> Focus on site/region-level analysis
```

---

## Common Analysis Patterns

### Pattern 1: Methylation Array Analysis
```
Input: Beta-value matrix + manifest + clinical data
Question: "How many CpGs are differentially methylated?"

Flow:
1. Load beta matrix, manifest, clinical data
2. Filter CpG probes (cg only, remove sex chr, variance filter)
3. Define groups from clinical data
4. Run differential_methylation()
5. Apply thresholds (padj < 0.05, |delta_beta| > 0.2)
6. Report count and direction (hyper/hypo)
```

### Pattern 2: Age-Related CpG Density
```
Input: Beta-value matrix + manifest + ages
Question: "What is the density ratio of age-related CpGs between chr1 and chr2?"

Flow:
1. Load beta matrix and ages from clinical data
2. Run identify_age_related_cpgs()
3. Filter significant age-related CpGs
4. Map to chromosomes using manifest
5. Calculate chromosome_cpg_density()
6. Compute ratio between specified chromosomes
```

### Pattern 3: Multi-Omics Missing Data
```
Input: Clinical + expression + methylation data files
Question: "How many patients have complete data for all modalities?"

Flow:
1. Load all data files
2. Extract sample IDs from each
3. Find intersection (common samples)
4. Check for NaN/missing within clinical variables
5. Report complete cases count
```

### Pattern 4: ChIP-seq Peak Annotation
```
Input: BED/narrowPeak file
Question: "What fraction of peaks are in promoter regions?"

Flow:
1. Load BED file with load_bed_file()
2. Load or fetch gene annotation (Ensembl)
3. Run annotate_peaks_to_genes()
4. Classify regions with classify_peak_regions()
5. Calculate fraction in promoters
```

### Pattern 5: Methylation-Expression Integration
```
Input: Beta matrix + expression matrix + probe-gene mapping
Question: "What is the correlation between methylation and expression?"

Flow:
1. Load both matrices
2. Build probe-gene map from manifest
3. Align samples across datasets
4. Run correlate_methylation_expression()
5. Report significant anti-correlations
```

---

## Edge Cases

### Missing Probe Annotation
When no manifest/annotation file is available:
- Extract chromosome from probe ID naming patterns if possible
- Use ToolUniverse Ensembl tools to build minimal annotation
- Report limitation: "chromosome mapping unavailable for X probes"

### Mixed Genome Builds
When data uses different builds:
- Detect build from context (data README, file names, known coordinates)
- Use appropriate chromosome lengths for density calculations
- Do NOT mix hg19 and hg38 coordinates

### Very Large Datasets
For datasets with >500K CpG sites:
- Use chunked processing for differential methylation
- Pre-filter by variance before statistical testing
- Use vectorized operations (avoid row-by-row loops where possible)

### Sample ID Mismatches
Clinical and molecular data may use different ID formats:
- TCGA: barcode (TCGA-XX-XXXX-01A) vs patient ID (TCGA-XX-XXXX)
- Try truncating or matching partial IDs
- Report number of matched/unmatched samples

---

## Fallback Strategies

| Scenario | Primary | Fallback |
|----------|---------|----------|
| No manifest file | Load from data dir | Build minimal from Ensembl lookup |
| No pybedtools | Pure Python overlap | pandas-based interval intersection |
| No pyBigWig | Skip BigWig analysis | Use pre-computed summary tables |
| Missing clinical data | Report missing | Use available samples only |
| Low sample count | Parametric test | Use non-parametric (Wilcoxon) |
| Large dataset (>500K probes) | Full analysis | Sample or chunk-based processing |
