# Quick Start: RNA-seq DESeq2 Analysis

## Prerequisites

```bash
pip install pydeseq2 gseapy pandas numpy scipy anndata statsmodels
```

## 5-Minute Workflow

### Step 1: Load Data

```python
import pandas as pd
import numpy as np

# Load count matrix (samples x genes or genes x samples)
counts = pd.read_csv("counts.csv", index_col=0)
metadata = pd.read_csv("metadata.csv", index_col=0)

# Orient: samples must be ROWS, genes must be COLUMNS
# If genes are rows (common for RNA-seq), transpose:
if counts.shape[0] > counts.shape[1] * 5:
    counts = counts.T

# Align samples
common = sorted(set(counts.index) & set(metadata.index))
counts = counts.loc[common]
metadata = metadata.loc[common]

# Ensure integer counts
counts = counts.round().astype(int)

print(f"Counts: {counts.shape[0]} samples x {counts.shape[1]} genes")
print(f"Conditions: {metadata['condition'].value_counts().to_dict()}")
```

### Step 2: Run DESeq2

```python
from pydeseq2.dds import DeseqDataSet
from pydeseq2.ds import DeseqStats

# Set reference level (first category = reference)
metadata['condition'] = pd.Categorical(
    metadata['condition'],
    categories=['control', 'treatment']
)

# Fit model
dds = DeseqDataSet(
    counts=counts,
    metadata=metadata,
    design="~condition",
    quiet=True
)
dds.deseq2()
```

### Step 3: Get Results

```python
# Extract contrast
stat_res = DeseqStats(
    dds,
    contrast=['condition', 'treatment', 'control'],
    quiet=True
)
stat_res.run_wald_test()
stat_res.summary()
results = stat_res.results_df

# Filter DEGs
sig = results[
    (results['padj'] < 0.05) &
    (results['log2FoldChange'].abs() > 0.5) &
    (results['baseMean'] >= 10)
]
print(f"Significant DEGs: {len(sig)} ({len(sig[sig['log2FoldChange']>0])} up, {len(sig[sig['log2FoldChange']<0])} down)")
```

### Step 4: LFC Shrinkage (Optional)

```python
# Apply apeglm-like LFC shrinkage
stat_res.lfc_shrink(coeff='condition[T.treatment]')
results_shrunk = stat_res.results_df
```

### Step 5: Enrichment Analysis (Optional)

```python
import gseapy as gp

enr = gp.enrich(
    gene_list=sig.index.tolist(),
    gene_sets='GO_Biological_Process_2021',
    outdir=None,
    no_plot=True,
    verbose=False
)
print(enr.results[['Term', 'Adjusted P-value', 'Overlap']].head(10))
```

---

## Common Recipes

### Recipe 1: Multi-Factor Design

```python
# Account for batch + condition
metadata['batch'] = pd.Categorical(metadata['batch'])
metadata['condition'] = pd.Categorical(
    metadata['condition'],
    categories=['WT', 'MUT1', 'MUT2']  # WT = reference
)

dds = DeseqDataSet(
    counts=counts,
    metadata=metadata,
    design="~batch + condition",
    quiet=True
)
dds.deseq2()

# Compare MUT1 vs WT
stat_res = DeseqStats(dds, contrast=['condition', 'MUT1', 'WT'], quiet=True)
stat_res.run_wald_test()
stat_res.summary()
```

### Recipe 2: Dispersion Diagnostics

```python
# How many genes have genewise dispersion below 1e-5?
dds.deseq2()
n_below = (dds.var['genewise_dispersions'] < 1e-5).sum()
print(f"Genes with dispersion < 1e-5: {n_below}")
```

### Recipe 3: Multi-Condition Unique DEGs

```python
# Genes DE in MUT1 but not in MUT2 or MUT3
degs_1 = set(filter_degs(res_mut1, padj_threshold=0.05).index)
degs_2 = set(filter_degs(res_mut2, padj_threshold=0.05).index)
degs_3 = set(filter_degs(res_mut3, padj_threshold=0.05).index)
unique_to_1 = degs_1 - degs_2 - degs_3
print(f"Unique to MUT1: {len(unique_to_1)}")
```

### Recipe 4: Specific Gene Lookup

```python
# Get padj and log2FC for gene GRIK5
gene = 'GRIK5'
if gene in results.index:
    padj = results.loc[gene, 'padj']
    lfc = results.loc[gene, 'log2FoldChange']
    print(f"{gene}: padj={padj:.2E}, log2FC={lfc:.2f}")
```

### Recipe 5: Multiple Testing Methods

```python
from statsmodels.stats.multitest import multipletests

pvals = results['pvalue'].dropna().values
_, padj_bh, _, _ = multipletests(pvals, method='fdr_bh')
_, padj_by, _, _ = multipletests(pvals, method='fdr_by')
_, padj_bonf, _, _ = multipletests(pvals, method='bonferroni')

print(f"BH significant: {(padj_bh < 0.05).sum()}")
print(f"BY significant: {(padj_by < 0.05).sum()}")
print(f"Bonferroni significant: {(padj_bonf < 0.05).sum()}")
```

### Recipe 6: KEGG/Reactome Enrichment

```python
import gseapy as gp

# KEGG enrichment for mouse
enr_kegg = gp.enrich(
    gene_list=sig.index.tolist(),
    gene_sets='KEGG_2019_Mouse',
    outdir=None,
    no_plot=True,
    verbose=False
)

# Reactome enrichment
enr_reactome = gp.enrich(
    gene_list=sig.index.tolist(),
    gene_sets='Reactome_2022',
    outdir=None,
    no_plot=True,
    verbose=False
)
```

### Recipe 7: Proportion Confidence Interval

```python
from statsmodels.stats.proportion import proportion_confint

n_total = len(results.dropna(subset=['padj']))
n_sig = len(sig)
ci_low, ci_high = proportion_confint(n_sig, n_total, method='wilson')
print(f"95% CI (Wilson): ({ci_low:.4f}, {ci_high:.4f})")
```
