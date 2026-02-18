# tooluniverse-epigenomics

Production-ready genomics and epigenomics data processing for BixBench questions.

## Overview

This skill provides comprehensive epigenomics data analysis capabilities:

- **Methylation Analysis**: Beta-value matrix processing, CpG filtering, differential methylation (t-test/Wilcoxon), age-related CpG detection, chromosome-level density
- **ChIP-seq Analysis**: BED/narrowPeak/broadPeak file parsing, peak statistics, gene annotation, region classification, overlap detection
- **ATAC-seq Analysis**: Chromatin accessibility quantification, nucleosome-free region (NFR) detection, region classification
- **Multi-Omics Integration**: Methylation-expression correlation, ChIP-seq + expression integration, cross-modality missing data analysis
- **Genome-Wide Statistics**: Chromosome-level CpG density, genome-wide averages, density ratios, multiple testing correction
- **ToolUniverse Annotation**: Regulatory context via Ensembl, ENCODE, SCREEN, JASPAR, ReMap, RegulomeDB, ChIPAtlas

## Installation

```bash
# Required
pip install pandas numpy scipy statsmodels

# Recommended (BAM/SAM support)
pip install pysam

# For ToolUniverse annotation
pip install tooluniverse
```

## Quick Start

```python
import pandas as pd
import numpy as np
from scipy import stats
import statsmodels.stats.multitest as mt

# Load methylation beta-value matrix (probes x samples)
beta = pd.read_csv('methylation_beta_values.csv', index_col=0)
clinical = pd.read_csv('clinical_data.csv', index_col=0)

# Define sample groups
tumor = [s for s in clinical[clinical['type'] == 'Tumor'].index if s in beta.columns]
normal = [s for s in clinical[clinical['type'] == 'Normal'].index if s in beta.columns]

# Differential methylation analysis
results = pd.DataFrame({
    'mean_tumor': beta[tumor].mean(axis=1),
    'mean_normal': beta[normal].mean(axis=1),
    'delta_beta': beta[tumor].mean(axis=1) - beta[normal].mean(axis=1),
})

pvalues = []
for probe in beta.index:
    v1 = beta.loc[probe, tumor].dropna().values
    v2 = beta.loc[probe, normal].dropna().values
    if len(v1) >= 2 and len(v2) >= 2:
        _, pval = stats.ttest_ind(v1, v2, equal_var=False)
        pvalues.append(pval)
    else:
        pvalues.append(np.nan)

results['pvalue'] = pvalues
valid = results['pvalue'].dropna()
reject, padj, _, _ = mt.multipletests(valid.values, method='fdr_bh')
results.loc[valid.index, 'padj'] = padj

sig = (results['padj'] < 0.05).sum()
print(f"Significant DMPs: {sig}")
```

## Files

| File | Description |
|------|-------------|
| `SKILL.md` | Detailed skill documentation with all phases, code, and tool references |
| `QUICK_START.md` | Practical usage examples (5 complete workflows) |
| `test_skill.py` | Comprehensive test suite (58 tests) |
| `README.md` | This file |

## Test Results

```
58/58 tests passed (100%)

Phase  1: Methylation Data Loading      -  5/5  PASS
Phase  2: CpG Probe Filtering           -  6/6  PASS
Phase  3: Differential Methylation       -  4/4  PASS
Phase  4: Age-Related CpGs              -  2/2  PASS
Phase  5: Chromosome Statistics          -  5/5  PASS
Phase  6: BED/Peak File Loading          -  4/4  PASS
Phase  7: Peak Annotation                -  2/2  PASS
Phase  8: Peak Overlap Detection         -  2/2  PASS
Phase  9: ATAC-seq Analysis              -  1/1  PASS
Phase 10: Multi-Omics Integration        -  2/2  PASS
Phase 11: Clinical Data Integration      -  2/2  PASS
Phase 12: Genome-Wide Statistics         -  3/3  PASS
Phase 13: Multiple Testing Correction    -  2/2  PASS
Phase 14: Manifest Processing            -  3/3  PASS
Phase 15: ToolUniverse Integration       -  6/6  PASS
Phase 16: BixBench-Style Questions       -  5/5  PASS
Phase 17: Edge Cases                     -  4/4  PASS
```

## Key Capabilities

### Methylation Analysis

| Capability | Method | Input | Output |
|-----------|--------|-------|--------|
| Load beta matrix | `pd.read_csv()` | CSV/TSV file | DataFrame (probes x samples) |
| Detect type | Value range check | DataFrame | 'beta' or 'mvalue' |
| Beta/M conversion | `log2(b/(1-b))` | DataFrame | Converted DataFrame |
| Filter probes | Variance, missing, type | DataFrame + criteria | Filtered DataFrame |
| Differential methylation | t-test / Wilcoxon | DataFrame + groups | DataFrame with padj |
| Age correlation | Pearson / Spearman | DataFrame + ages | DataFrame with padj |
| Chromosome density | CpGs / chr length | Probe list + manifest | Density dict |

### ChIP-seq / ATAC-seq Analysis

| Capability | Method | Input | Output |
|-----------|--------|-------|--------|
| Load BED/peaks | `pd.read_csv(sep='\t')` | BED file | DataFrame |
| Peak statistics | Length, coverage | Peak DataFrame | Stats dict |
| Gene annotation | Distance to TSS | Peaks + genes | Annotated DataFrame |
| Region classification | Promoter/body/distal | Peaks + genes | Region counts |
| Overlap detection | Interval intersection | Two BED DataFrames | Overlaps list |
| NFR analysis | Length < 150bp | ATAC peaks | NFR/nucleosome stats |

### Genome Builds Supported

| Build | Species | Autosomes | Sex Chromosomes |
|-------|---------|-----------|-----------------|
| hg38 (GRCh38) | Human | chr1-chr22 | chrX, chrY |
| hg19 (GRCh37) | Human | chr1-chr22 | chrX, chrY |
| mm10 (GRCm38) | Mouse | chr1-chr19 | chrX, chrY |

### ToolUniverse Integration

| Tool | Purpose | Parameters |
|------|---------|-----------|
| `ensembl_lookup_gene` | Gene coordinates | `gene_id`, `species` |
| `SCREEN_get_regulatory_elements` | cCREs near genes | `gene_name`, `element_type`, `limit` |
| `ENCODE_search_experiments` | ChIP-seq/ATAC experiments | `assay_title`, `target`, `organism` |
| `ChIPAtlas_get_experiments` | ChIP-seq datasets | `operation`, `genome`, `antigen` |
| `JASPAR_search_motifs` | Motif databases | `search`, `collection`, `species` |
| `ReMap_get_chip_seq_peaks` | TF binding peaks | `gene_name`, `cell_type`, `limit` |
| `RegulomeDB_get_variant_regulation` | Variant regulation | `rsid` |
| `ensembl_get_regulatory_features` | Regulatory elements | `region`, `feature`, `species` |

## Running Tests

```bash
python test_skill.py
```

## BixBench Question Types Supported

1. **Differential methylation**: "How many CpG sites show significant differential methylation?"
2. **Chromosome density**: "What is the ratio of age-related CpG density between chr19 and chr1?"
3. **Genome-wide statistics**: "What is the genome-wide average CpG density per base pair?"
4. **Multi-omics completeness**: "How many patients have complete data across all modalities?"
5. **Peak annotation**: "How many ChIP-seq peaks overlap with promoter regions?"
6. **Correlation analysis**: "What is the correlation between methylation and expression for gene X?"
7. **Filtering questions**: "After applying variance and missing data filters, how many probes remain?"

## License

Part of the ToolUniverse project.
