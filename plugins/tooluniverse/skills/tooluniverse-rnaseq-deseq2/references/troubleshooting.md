# Troubleshooting Guide

Common issues and solutions for RNA-seq analysis with PyDESeq2.

## Data Loading Issues

### "No matching samples between counts and metadata"

**Cause**: Sample names don't match between count matrix and metadata.

**Solutions**:

```python
# Check sample names
print("Count samples:", list(counts.index)[:5])
print("Metadata samples:", list(metadata.index)[:5])

# Try case-insensitive matching
counts.index = counts.index.str.lower()
metadata.index = metadata.index.str.lower()

# Remove whitespace
counts.index = counts.index.str.strip()
metadata.index = metadata.index.str.strip()

# Try transpose
if set(counts.columns) & set(metadata.index):
    counts = counts.T
```

### "Non-integer counts detected"

**Cause**: Data is normalized (FPKM, TPM) or has floating point values.

**Solutions**:

```python
# Option 1: Round to integers (acceptable if close to integers)
counts = counts.round().astype(int)

# Option 2: Use t-test instead of DESeq2 for normalized data
from scipy import stats
stat, pval = stats.ttest_ind(group1, group2)

# Check if data is truly raw counts
print(counts.head())
print("Min value:", counts.min().min())
print("Has decimals:", (counts % 1 != 0).any().any())
```

### Matrix orientation wrong

**Cause**: Genes are rows instead of columns.

**Solution**:

```python
# Check shape
print(f"Counts shape: {counts.shape}")  # Should be (n_samples, n_genes)
print(f"Samples >> genes? {counts.shape[0] > counts.shape[1] * 5}")

# Transpose if needed
if counts.shape[0] > counts.shape[1] * 5:
    counts = counts.T
```

## DESeq2 Execution Issues

### "Dispersion trend did not converge"

**Cause**: Small sample size or low variation.

**Solution**:

```python
# Use mean fit instead of parametric
dds = DeseqDataSet(
    counts=counts,
    metadata=metadata,
    design="~condition",
    fit_type='mean',  # Instead of 'parametric'
    quiet=True
)
dds.deseq2()
```

### "Contrast not found"

**Cause**: Wrong factor/level names in contrast.

**Solution**:

```python
# Check available levels
print("Available factors:", metadata.columns)
print("Condition levels:", metadata['condition'].unique())

# Verify exact names (case-sensitive)
contrast = ['condition', 'treatment', 'control']  # Must match exactly
```

### "All genes filtered out"

**Cause**: Too strict pre-filtering or all counts are zero.

**Solution**:

```python
# Check data quality
print("Zero genes:", (counts.sum(axis=0) == 0).sum())
print("Low count genes:", (counts.sum(axis=0) < 10).sum())

# Remove only zero genes
nonzero = counts.sum(axis=0) > 0
counts = counts.loc[:, nonzero]

# Don't pre-filter too aggressively
# DESeq2 handles low counts internally
```

### "Single replicate per condition"

**Cause**: Only 1 sample per condition - cannot estimate dispersion.

**Solution**:

```python
# Cannot run DESeq2 with single replicates
# Use fold-change only
mean_A = counts[samples_A].mean(axis=1)
mean_B = counts[samples_B].mean(axis=1)
log2fc = np.log2((mean_B + 1) / (mean_A + 1))

# Or pool replicates from similar conditions
```

## Reference Level Issues

### Wrong reference level

**Cause**: Reference level not set correctly.

**Solution**:

```python
# In PyDESeq2, FIRST category is reference
metadata['condition'] = pd.Categorical(
    metadata['condition'],
    categories=['control', 'treatment']  # Control first = reference
)

# Verify
print("Categories:", metadata['condition'].cat.categories)
print("First category (reference):", metadata['condition'].cat.categories[0])
```

## LFC Shrinkage Issues

### "Coefficient not found for shrinkage"

**Cause**: Wrong coefficient name format.

**Solution**:

```python
# Check available coefficients
print("Available coefficients:", list(dds.varm['LFC'].columns))

# Standard format: factor[T.level]
coeff = 'condition[T.treatment]'

# Verify before shrinking
if coeff in dds.varm['LFC'].columns:
    stat_res.lfc_shrink(coeff=coeff)
else:
    print(f"ERROR: '{coeff}' not found")
    print("Skipping shrinkage")
```

## Result Extraction Issues

### "NaN in padj column"

**Cause**: Independent filtering removed genes with insufficient evidence.

**Solution**:

```python
# This is EXPECTED behavior
# Remove NaN before counting DEGs
sig_genes = results.dropna(subset=['padj'])
sig_genes = sig_genes[sig_genes['padj'] < 0.05]

# Don't include NaN genes in counts
answer = len(sig_genes)  # Correct
# NOT: len(results[results['padj'] < 0.05])  # Wrong, includes NaN
```

### "Gene not found in results"

**Cause**: Gene name case mismatch or gene filtered out.

**Solution**:

```python
# Case-insensitive search
def find_gene(results_df, gene_name):
    # Exact match
    if gene_name in results_df.index:
        return gene_name

    # Case-insensitive
    idx_lower = {g.lower(): g for g in results_df.index}
    if gene_name.lower() in idx_lower:
        return idx_lower[gene_name.lower()]

    # Partial match
    matches = [g for g in results_df.index if gene_name.lower() in g.lower()]
    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1:
        print(f"Multiple matches: {matches}")

    return None

gene = find_gene(results, "TP53")
if gene:
    lfc = results.loc[gene, 'log2FoldChange']
```

## Enrichment Analysis Issues

### "No enrichment results"

**Cause**: Gene list too small or wrong organism/library.

**Solution**:

```python
# Check gene list
print(f"Gene list size: {len(gene_list)}")
print(f"Sample genes: {gene_list[:5]}")

# Try different libraries
libraries = [
    'GO_Biological_Process_2023',
    'GO_Biological_Process_2021',
    'KEGG_2021_Human',
    'KEGG_2019_Mouse'
]

for lib in libraries:
    try:
        enr = gp.enrich(gene_list=gene_list, gene_sets=lib, outdir=None, no_plot=True)
        if len(enr.results) > 0:
            print(f"✓ {lib}: {len(enr.results)} results")
            break
    except Exception as e:
        print(f"✗ {lib}: {e}")
```

### "gseapy organism parameter deprecated"

**Cause**: Using old gseapy syntax with `organism` parameter.

**Solution**:

```python
# OLD (doesn't work in gseapy >= 1.1)
# enr = gp.enrich(gene_list=gene_list, organism='human', gene_sets='GO_Biological_Process')

# NEW (correct)
enr = gp.enrich(
    gene_list=gene_list,
    gene_sets='GO_Biological_Process_2023',  # Organism in library name
    outdir=None
)
```

## Memory Issues

### "Memory error with large gene set"

**Cause**: Too many genes (60K+ genes with many samples).

**Solution**:

```python
# Pre-filter low-count genes
min_count = 10
keep = counts.sum(axis=0) >= min_count
counts_filtered = counts.loc[:, keep]
print(f"Kept {keep.sum()} / {len(keep)} genes")

# Use sparse matrices (if applicable)
from scipy.sparse import csr_matrix
counts_sparse = csr_matrix(counts.values)
```

## Multi-Factor Design Issues

### "Singular design matrix"

**Cause**: Confounded factors (e.g., batch perfectly correlated with condition).

**Solution**:

```python
# Check confounding
print(pd.crosstab(metadata['batch'], metadata['condition']))

# If confounded, cannot separate effects
# Remove confounded factor from design
design = "~condition"  # Remove batch if confounded
```

## Performance Issues

### "DESeq2 takes too long"

**Cause**: Large dataset or many factors.

**Solutions**:

```python
# Use parallel processing (if available)
import multiprocessing
n_cpus = multiprocessing.cpu_count()
# Note: PyDESeq2 doesn't directly support n_cpus, but numpy may use multiple cores

# Pre-filter more aggressively
min_count = 10
min_samples = 3
keep = (counts >= min_count).sum(axis=0) >= min_samples
counts_filtered = counts.loc[:, keep]

# Use mean fit instead of parametric (faster)
dds = DeseqDataSet(counts=counts, metadata=metadata, design="~condition",
                   fit_type='mean', quiet=True)
```

## Validation Issues

### Results don't match expected answer

**Checks**:

```python
# 1. Check reference level
print("Reference:", metadata['condition'].cat.categories[0])

# 2. Check contrast direction
print("Contrast:", contrast)  # [factor, numerator, denominator]

# 3. Check filtering thresholds
print(f"padj < {padj_threshold}")
print(f"|log2FC| > {lfc_threshold}")

# 4. Check if shrinkage was applied
print("Shrinkage applied:", 'lfcSE' in results.columns)

# 5. Check for NaN handling
print("Genes with NaN padj:", results['padj'].isna().sum())
```

## Debugging Checklist

Before reporting issues, verify:

- [ ] Count matrix has samples as rows, genes as columns
- [ ] Counts are non-negative integers
- [ ] Metadata index matches count matrix index exactly
- [ ] Design formula references valid column names in metadata
- [ ] Reference level is set correctly (first category in Categorical)
- [ ] Contrast factor and levels exist in metadata
- [ ] LFC shrinkage coefficient name matches pydeseq2 format
- [ ] Filtering thresholds match question exactly
- [ ] NaN values in padj are excluded from DEG counts

## Getting Help

```python
# Print diagnostic information
print("=" * 50)
print("DIAGNOSTIC INFORMATION")
print("=" * 50)
print(f"Counts shape: {counts.shape}")
print(f"Metadata shape: {metadata.shape}")
print(f"Design: {design}")
print(f"Reference level: {metadata['condition'].cat.categories[0]}")
print(f"Contrast: {contrast}")
print(f"PyDESeq2 version: {pydeseq2.__version__}")
print(f"\nSample counts:\n{counts.iloc[:3, :3]}")
print(f"\nMetadata:\n{metadata.head(3)}")
print(f"\nResults:\n{results.head(3)}")
print("=" * 50)
```
