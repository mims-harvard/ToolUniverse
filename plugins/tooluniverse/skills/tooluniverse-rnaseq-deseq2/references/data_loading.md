# Data Loading and Validation

Detailed guide for loading count matrices and metadata.

## Handling R Data Files (RDS)

If your data is in R format (`.rds`, `.RData`), convert to CSV first:

### Option 1: Convert in R (if available)

```r
# In R
result <- readRDS("deseq2_results.rds")
result_df <- as.data.frame(result)
write.csv(result_df, "deseq2_results.csv", row.names=TRUE)
```

Then load the CSV in Python as usual.

### Option 2: Use rpy2 in Python (requires R installed)

```python
import rpy2.robjects as ro
from rpy2.robjects import pandas2ri
pandas2ri.activate()

# Read RDS file
ro.r(f'df <- as.data.frame(readRDS("{rds_file}"))')

# Convert to pandas
df = pandas2ri.rpy2py(ro.r['df'])
```

**Note**: This requires R and the relevant R packages (e.g., DESeq2) installed. If unavailable, use Option 1 on a machine with R.

### Working with Pre-computed DESeq2 Results

If you have an RDS file containing DESeq2 results (not count data):

1. **Convert to CSV** (Option 1 or 2 above)
2. **Filter genes** directly in pandas:

```python
# Read pre-computed results
results = pd.read_csv("deseq2_results.csv", index_col=0)

# Filter upregulated genes
upregulated = results[
    (results['log2FoldChange'] > 0) &  # Positive = upregulated
    (results['padj'] < 0.05)            # Significant
]

# Get gene list
genes = upregulated.index.tolist()

# Use with /tooluniverse-gene-enrichment skill
```

3. **Skip to enrichment** - Use gene list with enrichment analysis (Step 5 in workflow)

## Load Count Matrix

```python
import pandas as pd
import numpy as np
import os

def load_count_matrix(file_path, **kwargs):
    """Load count matrix from various formats.

    Expects: genes as rows/columns, samples as rows/columns.
    PyDESeq2 requires: samples as rows, genes as columns.
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext in ['.csv']:
        df = pd.read_csv(file_path, index_col=0, **kwargs)
    elif ext in ['.tsv', '.txt']:
        df = pd.read_csv(file_path, sep='\t', index_col=0, **kwargs)
    elif ext in ['.h5ad']:
        import anndata
        adata = anndata.read_h5ad(file_path)
        df = pd.DataFrame(
            adata.X.toarray() if hasattr(adata.X, 'toarray') else adata.X,
            index=adata.obs_names,
            columns=adata.var_names
        )
        return df, adata.obs  # Return metadata too if available
    else:
        # Try tab-separated as default
        df = pd.read_csv(file_path, sep='\t', index_col=0, **kwargs)

    return df
```

## Orient Matrix

**CRITICAL**: PyDESeq2 expects samples as rows, genes as columns.

```python
def orient_count_matrix(df, metadata_samples=None):
    """Ensure samples are rows and genes are columns.

    Heuristic: if column count >> row count, genes are likely columns (correct).
    If row count >> column count, genes are likely rows (need transpose).
    If metadata_samples provided, match against index and columns.
    """
    if metadata_samples is not None:
        # Check if samples match rows or columns
        row_match = len(set(df.index) & set(metadata_samples))
        col_match = len(set(df.columns) & set(metadata_samples))
        if col_match > row_match:
            df = df.T
        return df

    # Heuristic: typical RNA-seq has 10-1000 samples and 10000-60000 genes
    if df.shape[0] > df.shape[1] * 5:  # Many more rows than columns
        df = df.T  # Transpose: genes were rows

    return df
```

## Load Metadata

```python
def load_metadata(file_path, **kwargs):
    """Load sample metadata (colData in R)."""
    ext = os.path.splitext(file_path)[1].lower()

    if ext in ['.csv']:
        meta = pd.read_csv(file_path, index_col=0, **kwargs)
    elif ext in ['.tsv', '.txt']:
        meta = pd.read_csv(file_path, sep='\t', index_col=0, **kwargs)
    else:
        meta = pd.read_csv(file_path, sep='\t', index_col=0, **kwargs)

    return meta
```

## Validate and Align

```python
def validate_inputs(counts, metadata):
    """Validate count matrix and metadata alignment."""
    issues = []

    # Check sample alignment
    count_samples = set(counts.index)
    meta_samples = set(metadata.index)

    if count_samples != meta_samples:
        common = count_samples & meta_samples
        if len(common) == 0:
            # Try matching columns
            if set(counts.columns) & meta_samples:
                counts = counts.T
                count_samples = set(counts.index)
                common = count_samples & meta_samples

        if len(common) > 0:
            counts = counts.loc[sorted(common)]
            metadata = metadata.loc[sorted(common)]
            issues.append(f"Aligned to {len(common)} common samples")
        else:
            issues.append("ERROR: No matching samples between counts and metadata")
            return None, None, issues

    # Ensure integer counts
    if counts.dtypes.apply(lambda x: x == float).any():
        if (counts % 1 == 0).all().all():
            counts = counts.astype(int)
        else:
            # Might be normalized data - round to integers for DESeq2
            issues.append("WARNING: Non-integer counts detected. Rounding to integers.")
            counts = counts.round().astype(int)

    # Remove genes with zero counts across all samples
    nonzero_mask = counts.sum(axis=0) > 0
    n_removed = (~nonzero_mask).sum()
    if n_removed > 0:
        counts = counts.loc[:, nonzero_mask]
        issues.append(f"Removed {n_removed} genes with zero counts across all samples")

    # Remove negative values
    if (counts < 0).any().any():
        issues.append("WARNING: Negative counts detected. Setting to 0.")
        counts = counts.clip(lower=0)

    return counts, metadata, issues
```

## Subset Samples

```python
def subset_samples(counts, metadata, condition_col, values=None, exclude=None):
    """Subset samples based on metadata conditions."""
    if values is not None:
        mask = metadata[condition_col].isin(values)
    elif exclude is not None:
        mask = ~metadata[condition_col].isin(exclude)
    else:
        return counts, metadata

    metadata = metadata[mask]
    counts = counts.loc[metadata.index]
    return counts, metadata
```

## Example: Load and Validate

```python
# Load data
counts = load_count_matrix("counts.csv")
metadata = load_metadata("metadata.csv")

# Orient if needed
counts = orient_count_matrix(counts, metadata.index)

# Validate and align
counts, metadata, issues = validate_inputs(counts, metadata)

# Print validation issues
for issue in issues:
    print(f"  {issue}")

# Subset if needed
counts, metadata = subset_samples(
    counts, metadata,
    condition_col='treatment',
    values=['control', 'treated']
)

print(f"\nFinal dimensions:")
print(f"  Counts: {counts.shape[0]} samples × {counts.shape[1]} genes")
print(f"  Metadata: {metadata.shape[0]} samples")
```

## Handling Different Input Formats

### CSV with genes as columns (correct)
```
,Gene1,Gene2,Gene3
Sample1,100,50,200
Sample2,120,60,180
```
No action needed.

### CSV with genes as rows (needs transpose)
```
,Sample1,Sample2,Sample3
Gene1,100,120,90
Gene2,50,60,45
```
Call `orient_count_matrix()`.

### H5AD (AnnData)
```python
import anndata
adata = anndata.read_h5ad("data.h5ad")
counts = pd.DataFrame(
    adata.X.toarray() if hasattr(adata.X, 'toarray') else adata.X,
    index=adata.obs_names,
    columns=adata.var_names
)
metadata = adata.obs
```

### Pre-normalized data (FPKM, TPM)
If data is NOT raw counts:
```python
# Option 1: Round to integers (acceptable for DESeq2)
counts = counts.round().astype(int)

# Option 2: Use t-test instead of DESeq2 (for normalized data)
from scipy import stats
stat, pval = stats.ttest_ind(group1, group2)
```

## Common Issues

| Issue | Symptom | Solution |
|-------|---------|----------|
| Samples don't match | "No matching samples" error | Check if transpose needed, strip whitespace |
| Float counts | "Non-integer counts" warning | Round to integers or use t-test |
| Sample name mismatch | Different # of samples | Use `set(counts.index) & set(metadata.index)` |
| Zero-count genes | All-zero columns | Pre-filter before DESeq2 |
| Negative counts | Impossible biology | Set to 0, investigate source |
