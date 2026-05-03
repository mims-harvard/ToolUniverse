# Dispersion Analysis and Diagnostics

Understanding and analyzing dispersion estimates in PyDESeq2.

## Dispersion Storage in PyDESeq2

**CRITICAL**: In PyDESeq2, dispersions are stored in `dds.var` (NOT `dds.varm`).

```python
# After running dds.deseq2()
disp_data = dds.var  # DataFrame with dispersion columns
```

## Dispersion Columns

```python
def get_dispersion_data(dds):
    """Extract all dispersion-related data from fitted DESeq2 model.

    Returns dict with:
        - genewise_dispersions: Per-gene maximum likelihood estimates
        - fitted_dispersions: Trend-fitted values
        - MAP_dispersions: Maximum a posteriori (after shrinkage to trend)
        - dispersions: Final dispersions used in testing
    """
    disp_data = {}

    # Key dispersion columns in dds.var
    disp_columns = [
        'genewise_dispersions',  # Pre-shrinkage (gene-wise MLE)
        'fitted_dispersions',     # Trend curve values
        'MAP_dispersions',        # Post-shrinkage (MAP estimates)
        'dispersions',            # Final (MAP or genewise for outliers)
    ]

    for col in disp_columns:
        if col in dds.var.columns:
            disp_data[col] = dds.var[col]

    return disp_data
```

## Question Phrasing to Dispersion Column Mapping

| Question Phrasing | Which Dispersion | PyDESeq2 Column |
|---|---|---|
| "prior to dispersion fitting" | Gene-wise MLE | `genewise_dispersions` |
| "prior to shrinkage" | Gene-wise MLE | `genewise_dispersions` |
| "before dispersion fitting" | Gene-wise MLE | `genewise_dispersions` |
| "fitted dispersions" | Trend curve | `fitted_dispersions` |
| "after shrinkage" / "MAP" | MAP estimates | `MAP_dispersions` |
| "dispersion estimate" (general) | Final | `dispersions` |

## Dispersion Diagnostics

```python
def dispersion_diagnostics(dds, threshold=1e-5):
    """Analyze dispersion estimates for diagnostics.

    Common BixBench question: "How many genes have a dispersion estimate
    below 1e-05 prior to dispersion fitting?"

    Answer: Count genewise_dispersions < threshold
    """
    disp_data = get_dispersion_data(dds)

    diagnostics = {}

    if 'genewise_dispersions' in disp_data:
        gwd = disp_data['genewise_dispersions']
        diagnostics['genewise_below_threshold'] = (gwd < threshold).sum()
        diagnostics['genewise_min'] = gwd.min()
        diagnostics['genewise_max'] = gwd.max()
        diagnostics['genewise_median'] = gwd.median()
        diagnostics['genewise_mean'] = gwd.mean()

    if 'fitted_dispersions' in disp_data:
        fd = disp_data['fitted_dispersions']
        diagnostics['fitted_below_threshold'] = (fd < threshold).sum()
        diagnostics['fitted_min'] = fd.min()
        diagnostics['fitted_max'] = fd.max()
        diagnostics['fitted_median'] = fd.median()

    if 'MAP_dispersions' in disp_data:
        mapd = disp_data['MAP_dispersions']
        diagnostics['MAP_below_threshold'] = (mapd < threshold).sum()
        diagnostics['MAP_min'] = mapd.min()
        diagnostics['MAP_max'] = mapd.max()
        diagnostics['MAP_median'] = mapd.median()

    if 'dispersions' in disp_data:
        d = disp_data['dispersions']
        diagnostics['final_below_threshold'] = (d < threshold).sum()

    return diagnostics
```

## Common Questions

### Count genes below threshold

```python
# "How many genes have dispersion below 1e-5 prior to fitting?"
genewise = dds.var['genewise_dispersions']
answer = (genewise < 1e-5).sum()
```

### Count genes after shrinkage

```python
# "How many genes have dispersion below 1e-5 after shrinkage?"
map_disp = dds.var['MAP_dispersions']
answer = (map_disp < 1e-5).sum()
```

### Range of dispersions

```python
# "What is the range of gene-wise dispersions?"
genewise = dds.var['genewise_dispersions']
min_disp = genewise.min()
max_disp = genewise.max()
answer = f"{min_disp:.2E} to {max_disp:.2E}"
```

### Median dispersion

```python
# "What is the median dispersion estimate?"
median_disp = dds.var['dispersions'].median()
answer = f"{median_disp:.2E}"
```

## Dispersion Shrinkage Effect

```python
def analyze_shrinkage_effect(dds):
    """Compare gene-wise vs MAP dispersions to assess shrinkage."""
    genewise = dds.var['genewise_dispersions']
    map_disp = dds.var['MAP_dispersions']

    # Genes where shrinkage reduced dispersion
    shrunk_genes = (map_disp < genewise).sum()

    # Genes where shrinkage increased dispersion
    expanded_genes = (map_disp > genewise).sum()

    # Median fold change
    fold_change = map_disp / genewise
    median_fc = fold_change.median()

    results = {
        'shrunk_genes': shrunk_genes,
        'expanded_genes': expanded_genes,
        'median_fold_change': median_fc,
        'mean_genewise': genewise.mean(),
        'mean_MAP': map_disp.mean()
    }

    return results
```

## Outlier Detection

```python
def identify_dispersion_outliers(dds, threshold=10):
    """Identify genes with outlier dispersions.

    Outliers are genes where genewise dispersion is far from fitted.
    """
    genewise = dds.var['genewise_dispersions']
    fitted = dds.var['fitted_dispersions']

    # Ratio of genewise to fitted
    ratio = genewise / fitted

    # Outliers: ratio > threshold
    outliers = ratio > threshold
    outlier_genes = dds.var.index[outliers]

    return outlier_genes.tolist()
```

## Dispersion vs Mean Expression

```python
import matplotlib.pyplot as plt
import numpy as np

def plot_dispersion_trend(dds):
    """Plot dispersion vs mean expression (dispersion plot)."""
    baseMean = dds.var['baseMean']
    genewise = dds.var['genewise_dispersions']
    fitted = dds.var['fitted_dispersions']
    map_disp = dds.var['MAP_dispersions']

    plt.figure(figsize=(10, 6))
    plt.scatter(baseMean, genewise, s=1, alpha=0.3, label='Gene-wise', color='gray')
    plt.scatter(baseMean, map_disp, s=1, alpha=0.5, label='MAP', color='blue')

    # Plot fitted curve
    sorted_idx = baseMean.argsort()
    plt.plot(baseMean.iloc[sorted_idx], fitted.iloc[sorted_idx],
             color='red', linewidth=2, label='Fitted trend')

    plt.xscale('log')
    plt.yscale('log')
    plt.xlabel('Base Mean Expression')
    plt.ylabel('Dispersion')
    plt.legend()
    plt.title('Dispersion Estimates')
    plt.tight_layout()
    plt.savefig('dispersion_plot.png', dpi=150)
    plt.close()
```

## Dispersion Fitting Convergence

```python
def check_dispersion_convergence(dds):
    """Check if dispersion fitting converged properly."""
    fitted = dds.var['fitted_dispersions']

    # Check for NaN or Inf values
    has_nan = fitted.isna().any()
    has_inf = np.isinf(fitted).any()

    # Check if fitted values are reasonable
    min_fitted = fitted.min()
    max_fitted = fitted.max()

    convergence_ok = not (has_nan or has_inf) and (min_fitted > 0) and (max_fitted < 1e6)

    return {
        'converged': convergence_ok,
        'has_nan': has_nan,
        'has_inf': has_inf,
        'min_fitted': min_fitted,
        'max_fitted': max_fitted
    }
```

## Alternative Dispersion Fitting

```python
# If parametric fitting fails, use mean fitting
try:
    dds = DeseqDataSet(counts=counts, metadata=metadata,
                      design="~condition", fit_type='parametric', quiet=True)
    dds.deseq2()
except Exception as e:
    print(f"Parametric fit failed: {e}")
    print("Retrying with fit_type='mean'")
    dds = DeseqDataSet(counts=counts, metadata=metadata,
                      design="~condition", fit_type='mean', quiet=True)
    dds.deseq2()
```

## Dispersion by Gene Expression Level

```python
def dispersion_by_expression_level(dds, quantiles=[0.25, 0.5, 0.75]):
    """Analyze dispersion across expression level quantiles."""
    baseMean = dds.var['baseMean']
    dispersions = dds.var['dispersions']

    results = {}
    for q in quantiles:
        threshold = baseMean.quantile(q)
        genes_below = baseMean <= threshold
        median_disp = dispersions[genes_below].median()
        results[f'Q{int(q*100)}'] = {
            'expression_threshold': threshold,
            'median_dispersion': median_disp,
            'n_genes': genes_below.sum()
        }

    return results
```

## Complete Example

```python
from pydeseq2.dds import DeseqDataSet

# Run DESeq2
dds = DeseqDataSet(counts=counts, metadata=metadata, design="~condition", quiet=True)
dds.deseq2()

# Question: "How many genes have dispersion below 1e-5 prior to fitting?"
genewise = dds.var['genewise_dispersions']
answer = (genewise < 1e-5).sum()
print(f"Genes with dispersion < 1e-5 (prior to fitting): {answer}")

# Additional diagnostics
diag = dispersion_diagnostics(dds, threshold=1e-5)
print(f"\nDispersion diagnostics:")
print(f"  Gene-wise below threshold: {diag['genewise_below_threshold']}")
print(f"  Gene-wise median: {diag['genewise_median']:.2E}")
print(f"  MAP below threshold: {diag['MAP_below_threshold']}")
print(f"  MAP median: {diag['MAP_median']:.2E}")

# Shrinkage effect
shrinkage = analyze_shrinkage_effect(dds)
print(f"\nShrinkage effect:")
print(f"  Genes with reduced dispersion: {shrinkage['shrunk_genes']}")
print(f"  Median fold change: {shrinkage['median_fold_change']:.2f}")

# Check convergence
conv = check_dispersion_convergence(dds)
print(f"\nDispersion fitting convergence: {'OK' if conv['converged'] else 'FAILED'}")
```

## BixBench Pattern Examples

### Pattern: Count below threshold prior to fitting

```python
# Question: "How many genes have a dispersion estimate below 1e-05 prior to dispersion fitting?"
genewise = dds.var['genewise_dispersions']
answer = (genewise < 1e-5).sum()
```

### Pattern: Median dispersion

```python
# Question: "What is the median dispersion after shrinkage?"
map_disp = dds.var['MAP_dispersions']
answer = round(map_disp.median(), 6)
```

### Pattern: Range of dispersions

```python
# Question: "What is the minimum gene-wise dispersion?"
genewise = dds.var['genewise_dispersions']
answer = f"{genewise.min():.2E}"
```
