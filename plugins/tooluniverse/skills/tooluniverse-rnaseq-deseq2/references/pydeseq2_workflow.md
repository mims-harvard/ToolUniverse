# PyDESeq2 Complete Workflow

Comprehensive code examples for PyDESeq2 analysis.

## Basic Single-Factor Analysis

```python
import pandas as pd
from pydeseq2.dds import DeseqDataSet
from pydeseq2.ds import DeseqStats

# Assume counts and metadata are already loaded and validated

# Set reference level (first category becomes reference)
metadata['condition'] = pd.Categorical(
    metadata['condition'],
    categories=['control', 'treatment']  # control is reference
)

# Create DESeq2 dataset
dds = DeseqDataSet(
    counts=counts,
    metadata=metadata,
    design="~condition",
    quiet=True
)

# Run DESeq2 pipeline (normalization + dispersion + testing)
dds.deseq2()

# Extract results for contrast
stat_res = DeseqStats(
    dds,
    contrast=['condition', 'treatment', 'control'],
    alpha=0.05,
    quiet=True
)
stat_res.run_wald_test()
stat_res.summary()

# Get results DataFrame
results = stat_res.results_df
```

## Multi-Factor Design

```python
# Design with multiple factors
metadata['strain'] = pd.Categorical(metadata['strain'], categories=['WT', 'mutant'])
metadata['media'] = pd.Categorical(metadata['media'], categories=['LB', 'M9'])

# Multi-factor design
dds = DeseqDataSet(
    counts=counts,
    metadata=metadata,
    design="~strain + media",  # Additive model
    quiet=True
)
dds.deseq2()

# Extract results for strain effect (controlling for media)
stat_res = DeseqStats(dds, contrast=['strain', 'mutant', 'WT'], quiet=True)
stat_res.run_wald_test()
stat_res.summary()
results_strain = stat_res.results_df
```

## Interaction Design

```python
# Design with interaction term
dds = DeseqDataSet(
    counts=counts,
    metadata=metadata,
    design="~strain + treatment + strain:treatment",
    quiet=True
)
dds.deseq2()

# Main effect of treatment
stat_res_treatment = DeseqStats(dds, contrast=['treatment', 'treated', 'control'], quiet=True)
stat_res_treatment.run_wald_test()

# Interaction effect (requires coefficient name)
# Check available coefficients
print(dds.varm['LFC'].columns)  # View all coefficients

# Extract interaction results
stat_res_interaction = DeseqStats(dds, quiet=True)
# Note: interaction testing requires specifying coefficient directly
```

## Batch Effect Correction

```python
# Include batch as covariate
metadata['batch'] = pd.Categorical(metadata['batch'])
metadata['condition'] = pd.Categorical(metadata['condition'], categories=['control', 'treatment'])

dds = DeseqDataSet(
    counts=counts,
    metadata=metadata,
    design="~batch + condition",  # Batch first
    quiet=True
)
dds.deseq2()

# Extract condition effect (adjusted for batch)
stat_res = DeseqStats(dds, contrast=['condition', 'treatment', 'control'], quiet=True)
stat_res.run_wald_test()
stat_res.summary()
results = stat_res.results_df
```

## Continuous Covariates

```python
# Design with continuous variable (e.g., age, time)
dds = DeseqDataSet(
    counts=counts,
    metadata=metadata,
    design="~age + condition",
    continuous_factors=['age'],  # Specify continuous variables
    quiet=True
)
dds.deseq2()

# Extract condition effect (adjusted for age)
stat_res = DeseqStats(dds, contrast=['condition', 'treatment', 'control'], quiet=True)
stat_res.run_wald_test()
results = stat_res.results_df
```

## LFC Shrinkage

```python
# After running Wald test, apply shrinkage
stat_res = DeseqStats(dds, contrast=['condition', 'treatment', 'control'], quiet=True)
stat_res.run_wald_test()

# Determine coefficient name for shrinkage
# Format: factor[T.level] where level is the numerator
coeff = 'condition[T.treatment]'

# Verify coefficient exists
if coeff in dds.varm['LFC'].columns:
    stat_res.lfc_shrink(coeff=coeff)
else:
    print(f"WARNING: Coefficient '{coeff}' not found.")
    print(f"Available: {list(dds.varm['LFC'].columns)}")

results = stat_res.results_df
```

## Set Reference Level

**CRITICAL**: In PyDESeq2 v0.5.4+, use `pd.Categorical` with ordered categories. The FIRST category is the reference.

```python
def set_reference_level(metadata, factor_col, ref_value):
    """Set reference level for a factor by reordering Categorical.

    The FIRST category becomes the reference level in PyDESeq2.
    """
    current_cats = metadata[factor_col].unique().tolist()
    if ref_value not in current_cats:
        raise ValueError(f"Reference '{ref_value}' not in categories: {current_cats}")

    # Put reference first
    ordered_cats = [ref_value] + [c for c in current_cats if c != ref_value]
    metadata[factor_col] = pd.Categorical(
        metadata[factor_col],
        categories=ordered_cats
    )
    return metadata

# Usage
metadata = set_reference_level(metadata, 'condition', 'wildtype')
```

## Multiple Contrasts

```python
# Run DESeq2 once
dds = DeseqDataSet(counts=counts, metadata=metadata, design="~condition", quiet=True)
dds.deseq2()

# Extract multiple contrasts
contrasts = [
    ['condition', 'A', 'control'],
    ['condition', 'B', 'control'],
    ['condition', 'C', 'control']
]

results_dict = {}
for contrast in contrasts:
    stat_res = DeseqStats(dds, contrast=contrast, quiet=True)
    stat_res.run_wald_test()
    stat_res.summary()
    contrast_name = f"{contrast[1]}_vs_{contrast[2]}"
    results_dict[contrast_name] = stat_res.results_df
```

## Alternative Multiple Testing Correction

```python
from statsmodels.stats.multitest import multipletests
import numpy as np

# Run DESeq2 with default BH correction
stat_res = DeseqStats(dds, contrast=['condition', 'treatment', 'control'], quiet=True)
stat_res.run_wald_test()
results = stat_res.results_df

# Apply alternative correction
pvalues = results['pvalue'].values
mask = ~np.isnan(pvalues)

# Bonferroni
_, results.loc[mask, 'padj_bonf'], _, _ = multipletests(pvalues[mask], method='bonferroni')

# Benjamini-Yekutieli
_, results.loc[mask, 'padj_by'], _, _ = multipletests(pvalues[mask], method='fdr_by')

# Holm
_, results.loc[mask, 'padj_holm'], _, _ = multipletests(pvalues[mask], method='holm')
```

## Dispersion Fitting Options

```python
# Parametric fit (default, recommended for large samples)
dds = DeseqDataSet(counts=counts, metadata=metadata, design="~condition", fit_type='parametric')
dds.deseq2()

# Mean fit (for small samples or when parametric fails)
dds = DeseqDataSet(counts=counts, metadata=metadata, design="~condition", fit_type='mean')
dds.deseq2()

# If dispersion trend doesn't converge, use mean
try:
    dds = DeseqDataSet(counts=counts, metadata=metadata, design="~condition", fit_type='parametric')
    dds.deseq2()
except Exception as e:
    print(f"Parametric fit failed: {e}")
    print("Retrying with fit_type='mean'")
    dds = DeseqDataSet(counts=counts, metadata=metadata, design="~condition", fit_type='mean')
    dds.deseq2()
```

## Access Normalized Counts

```python
# After running dds.deseq2(), normalized counts are available
normalized_counts = dds.obsm['normed_counts']  # DataFrame, same shape as counts

# Size factors
size_factors = dds.obs['size_factors']

# Manual normalization
manual_norm = counts.div(size_factors, axis=0)
```

## Cook's Distance Filtering

```python
# Set minimum replicates for Cook's filtering
dds = DeseqDataSet(
    counts=counts,
    metadata=metadata,
    design="~condition",
    min_replicates=7,  # Default is 7
    quiet=True
)
dds.deseq2()

# Genes with Cook's outliers will have padj = NA
# These are automatically excluded in downstream filtering
```

## Pre-filtering Low-Count Genes

```python
# Filter genes with low mean counts before DESeq2 (optional, improves speed)
min_count = 10
keep_genes = counts.sum(axis=0) >= min_count
counts_filtered = counts.loc[:, keep_genes]

# Then run DESeq2 on filtered data
dds = DeseqDataSet(counts=counts_filtered, metadata=metadata, design="~condition", quiet=True)
dds.deseq2()
```

## Complete Example: Multi-Factor with Shrinkage

```python
import pandas as pd
from pydeseq2.dds import DeseqDataSet
from pydeseq2.ds import DeseqStats

# Load and validate data (from data_loading.md)
counts = pd.read_csv("counts.csv", index_col=0)
metadata = pd.read_csv("metadata.csv", index_col=0)

# Orient and validate
if counts.shape[0] > counts.shape[1] * 5:
    counts = counts.T
common = sorted(set(counts.index) & set(metadata.index))
counts = counts.loc[common].astype(int)
metadata = metadata.loc[common]

# Set reference levels
metadata['strain'] = pd.Categorical(metadata['strain'], categories=['WT', 'mutant'])
metadata['replicate'] = pd.Categorical(metadata['replicate'])

# Create and fit DESeq2 model
dds = DeseqDataSet(
    counts=counts,
    metadata=metadata,
    design="~replicate + strain",
    quiet=True
)
dds.deseq2()

# Extract results with shrinkage
stat_res = DeseqStats(dds, contrast=['strain', 'mutant', 'WT'], quiet=True)
stat_res.run_wald_test()
stat_res.summary()
stat_res.lfc_shrink(coeff='strain[T.mutant]')

results = stat_res.results_df

# Filter DEGs
sig_genes = results[
    (results['padj'] < 0.05) &
    (results['log2FoldChange'].abs() > 0.5)
]

print(f"Significant DEGs: {len(sig_genes)}")
print(f"Upregulated: {(sig_genes['log2FoldChange'] > 0).sum()}")
print(f"Downregulated: {(sig_genes['log2FoldChange'] < 0).sum()}")
```
