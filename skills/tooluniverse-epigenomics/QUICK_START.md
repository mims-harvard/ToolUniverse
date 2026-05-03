# Genomics & Epigenomics Data Processing - Quick Start

## Overview

This skill processes epigenomics data files (methylation arrays, ChIP-seq peaks, ATAC-seq data) and answers quantitative questions using pure Python (pandas, scipy, statsmodels) plus ToolUniverse annotation tools. Designed for BixBench-style questions about CpG sites, differential methylation, chromatin accessibility, and multi-omics integration.

---

## Quick Start Examples

### Example 1: Differential Methylation Analysis

**Question**: "How many CpG sites show significant differential methylation between tumor and normal?"

```python
import pandas as pd
import numpy as np
from scipy import stats
import statsmodels.stats.multitest as mt

# Load data
beta = pd.read_csv('methylation_beta_values.csv', index_col=0)
clinical = pd.read_csv('clinical_data.csv', index_col=0)

# Define groups
tumor_samples = clinical[clinical['sample_type'] == 'Tumor'].index.tolist()
normal_samples = clinical[clinical['sample_type'] == 'Normal'].index.tolist()

# Filter to common samples
tumor_samples = [s for s in tumor_samples if s in beta.columns]
normal_samples = [s for s in normal_samples if s in beta.columns]

# Differential methylation (vectorized for speed)
g1 = beta[tumor_samples]
g2 = beta[normal_samples]

results = pd.DataFrame({
    'mean_tumor': g1.mean(axis=1),
    'mean_normal': g2.mean(axis=1),
    'delta_beta': g1.mean(axis=1) - g2.mean(axis=1),
})

# T-test per probe
pvalues = []
for probe in beta.index:
    vals1 = g1.loc[probe].dropna().values
    vals2 = g2.loc[probe].dropna().values
    if len(vals1) >= 2 and len(vals2) >= 2:
        _, pval = stats.ttest_ind(vals1, vals2, equal_var=False)
        pvalues.append(pval)
    else:
        pvalues.append(np.nan)

results['pvalue'] = pvalues
valid = results['pvalue'].dropna()
reject, padj, _, _ = mt.multipletests(valid.values, method='fdr_bh')
results.loc[valid.index, 'padj'] = padj

# Count significant
n_sig = (results['padj'] < 0.05).sum()
print(f"Significant DMPs (padj < 0.05): {n_sig}")
```

---

### Example 2: Age-Related CpG Chromosome Density

**Question**: "What is the ratio of filtered age-related CpG density between chr19 and chr1?"

```python
import pandas as pd
import numpy as np
from scipy import stats
import statsmodels.stats.multitest as mt

# Load data
beta = pd.read_csv('methylation_beta_values.csv', index_col=0)
manifest = pd.read_csv('probe_manifest.csv')
clinical = pd.read_csv('clinical_data.csv', index_col=0)

# Get ages
ages = clinical['age_at_diagnosis'].values

# Correlate each probe with age
correlations = []
for probe in beta.index:
    vals = beta.loc[probe].values
    mask = ~np.isnan(vals) & ~np.isnan(ages)
    if sum(mask) >= 5:
        corr, pval = stats.pearsonr(ages[mask], vals[mask])
        correlations.append({'probe': probe, 'corr': corr, 'pvalue': pval})

corr_df = pd.DataFrame(correlations).set_index('probe')
reject, padj, _, _ = mt.multipletests(corr_df['pvalue'].values, method='fdr_bh')
corr_df['padj'] = padj

# Filter significant age-related CpGs
age_cpgs = corr_df[corr_df['padj'] < 0.05].index.tolist()

# Map to chromosomes
def normalize_chr(c):
    c = str(c).strip()
    return f'chr{c}' if not str(c).startswith('chr') else c

manifest_idx = manifest.set_index('Name')  # or 'probe_id'
probe_chrs = manifest_idx.loc[manifest_idx.index.isin(age_cpgs), 'CHR']
probe_chrs = probe_chrs.apply(normalize_chr)
chr_counts = probe_chrs.value_counts()

# Chromosome lengths (hg38)
chr_lengths = {
    'chr1': 248956422, 'chr19': 58617616,
    # ... (full dict in SKILL.md)
}

# Calculate density
density_19 = chr_counts.get('chr19', 0) / chr_lengths['chr19']
density_1 = chr_counts.get('chr1', 0) / chr_lengths['chr1']
ratio = density_19 / density_1
print(f"chr19/chr1 density ratio: {ratio:.4f}")
```

---

### Example 3: Multi-Omics Missing Data Analysis

**Question**: "How many patients have no missing data for vital status, gene expression, and methylation data?"

```python
import pandas as pd

# Load data
clinical = pd.read_csv('clinical_data.csv', index_col=0)
expression = pd.read_csv('expression_matrix.csv', index_col=0)  # genes x samples
methylation = pd.read_csv('methylation_beta.csv', index_col=0)  # probes x samples

# Get samples with vital_status
clinical_with_vital = set(clinical[clinical['vital_status'].notna()].index)

# Get samples in expression data
expression_samples = set(expression.columns)

# Get samples in methylation data
methylation_samples = set(methylation.columns)

# Intersection
complete = clinical_with_vital & expression_samples & methylation_samples
print(f"Patients with complete data: {len(complete)}")
```

---

### Example 4: ChIP-seq Peak Analysis

**Question**: "How many ChIP-seq peaks overlap with promoter regions?"

```python
import pandas as pd

# Load peak file
peaks = pd.read_csv('H3K27ac_peaks.narrowPeak', sep='\t', header=None,
    names=['chrom', 'start', 'end', 'name', 'score', 'strand',
           'signalValue', 'pValue', 'qValue', 'peak'])

# Load gene annotation (or use Ensembl via ToolUniverse)
genes = pd.read_csv('gene_annotation.bed', sep='\t',
    names=['chr', 'start', 'end', 'gene_name', 'score', 'strand'])

# Define promoters (TSS +/- 2000bp)
promoters = genes.copy()
promoters['prom_start'] = promoters.apply(
    lambda g: g['start'] - 2000 if g['strand'] == '+' else g['end'] - 2000, axis=1)
promoters['prom_end'] = promoters.apply(
    lambda g: g['start'] + 500 if g['strand'] == '+' else g['end'] + 500, axis=1)

# Count overlaps (pure Python)
n_promoter_peaks = 0
for _, peak in peaks.iterrows():
    chr_proms = promoters[promoters['chr'] == peak['chrom']]
    overlap = chr_proms[
        (chr_proms['prom_start'] < peak['end']) &
        (chr_proms['prom_end'] > peak['start'])
    ]
    if len(overlap) > 0:
        n_promoter_peaks += 1

print(f"Peaks in promoters: {n_promoter_peaks}/{len(peaks)} ({100*n_promoter_peaks/len(peaks):.1f}%)")
```

---

### Example 5: Genome-Wide CpG Density

**Question**: "What is the genome-wide average chromosomal density of unique age-related CpGs per base pair?"

```python
# After identifying age-related CpGs and chromosome mapping (Example 2)
total_cpgs = chr_counts.sum()
total_genome_length = sum(chr_lengths[c] for c in chr_counts.index if c in chr_lengths)
genome_wide_density = total_cpgs / total_genome_length
print(f"Genome-wide density: {genome_wide_density:.2e} CpGs/bp")
```

---

## ToolUniverse Annotation

Use ToolUniverse for biological context after computational analysis:

```python
from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()

# Annotate genes from differential methylation
gene = "TP53"
ens = tu.tools.ensembl_lookup_gene(id=gene, species='homo_sapiens')

# Get regulatory elements near a gene
screen = tu.tools.SCREEN_get_regulatory_elements(
    gene_name="TP53", element_type="enhancer", limit=10
)

# Find ChIP-seq experiments for histone mark
chipatlas = tu.tools.ChIPAtlas_get_experiments(
    operation="get_experiment_list",
    genome="hg38",
    antigen="H3K27ac",
    limit=20
)

# Get regulatory features for a region
ensembl_reg = tu.tools.ensembl_get_regulatory_features(
    region="17:7661779-7687550",  # No "chr" prefix
    feature="regulatory",
    species="human"
)
```

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

## Genome Builds Supported

| Build | Species | Autosomes | Sex Chromosomes |
|-------|---------|-----------|-----------------|
| hg38 (GRCh38) | Human | chr1-chr22 | chrX, chrY |
| hg19 (GRCh37) | Human | chr1-chr22 | chrX, chrY |
| mm10 (GRCm38) | Mouse | chr1-chr19 | chrX, chrY |
