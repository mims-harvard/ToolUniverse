# Result Filtering and Extraction

Advanced filtering patterns for DESeq2 results.

## Basic Filtering

```python
def filter_degs(results_df, padj_threshold=0.05, lfc_threshold=0,
                basemean_threshold=0, direction='both'):
    """Filter differentially expressed genes.

    Args:
        results_df: DESeq2 results DataFrame
        padj_threshold: Adjusted p-value cutoff
        lfc_threshold: Absolute log2 fold change cutoff (0 = no filter)
        basemean_threshold: Minimum mean expression
        direction: 'both', 'up', or 'down'

    Returns:
        Filtered DataFrame
    """
    df = results_df.dropna(subset=['padj'])  # Remove NaN padj

    # Apply filters
    mask = df['padj'] < padj_threshold

    if lfc_threshold > 0:
        mask = mask & (df['log2FoldChange'].abs() > lfc_threshold)

    if basemean_threshold > 0:
        mask = mask & (df['baseMean'] >= basemean_threshold)

    if direction == 'up':
        mask = mask & (df['log2FoldChange'] > 0)
    elif direction == 'down':
        mask = mask & (df['log2FoldChange'] < 0)

    return df[mask]
```

## Extract Specific Gene Results

```python
def get_gene_result(results_df, gene_name, column='log2FoldChange'):
    """Get a specific value for a specific gene.

    Handles case-insensitive matching and common naming issues.
    """
    # Try exact match first
    if gene_name in results_df.index:
        return results_df.loc[gene_name, column]

    # Case-insensitive match
    idx_lower = {g.lower(): g for g in results_df.index}
    if gene_name.lower() in idx_lower:
        actual_name = idx_lower[gene_name.lower()]
        return results_df.loc[actual_name, column]

    # Partial match (for gene IDs like PA14_35160)
    matches = [g for g in results_df.index if gene_name.lower() in g.lower()]
    if len(matches) == 1:
        return results_df.loc[matches[0], column]
    elif len(matches) > 1:
        return {m: results_df.loc[m, column] for m in matches}

    return None  # Gene not found
```

## Top N Genes

```python
# Top upregulated by log2FC
top_up = results.sort_values('log2FoldChange', ascending=False).head(10)

# Top downregulated by log2FC
top_down = results.sort_values('log2FoldChange').head(10)

# Top by adjusted p-value (most significant)
top_sig = results.sort_values('padj').head(10)

# Top by baseMean (highest expression)
top_expr = results.sort_values('baseMean', ascending=False).head(10)
```

## Quantile Filtering

```python
# Top 10% by log2FC magnitude
lfc_threshold = results['log2FoldChange'].abs().quantile(0.9)
top_10_percent = results[results['log2FoldChange'].abs() >= lfc_threshold]

# Top quartile by baseMean
basemean_threshold = results['baseMean'].quantile(0.75)
high_expr = results[results['baseMean'] >= basemean_threshold]
```

## Combined Filtering

```python
# Significant AND highly expressed
sig_high = results[
    (results['padj'] < 0.05) &
    (results['log2FoldChange'].abs() > 1) &
    (results['baseMean'] > results['baseMean'].median())
]

# Significant OR high fold change
sig_or_high_fc = results[
    (results['padj'] < 0.05) |
    (results['log2FoldChange'].abs() > 2)
]
```

## Set Operations on DEG Lists

```python
def compare_deg_sets(deg_sets, operation='unique'):
    """Compare DEG sets across conditions.

    Args:
        deg_sets: Dict of {condition_name: set_of_gene_names}
        operation: 'unique' (per condition), 'shared' (intersection),
                   'union', 'venn' (all combinations)

    Returns:
        Dict with results
    """
    results = {}
    condition_names = list(deg_sets.keys())
    all_genes = set()
    for genes in deg_sets.values():
        all_genes |= genes

    if operation == 'unique':
        # Genes unique to each condition (not in any other)
        for cond in condition_names:
            others = set()
            for other_cond in condition_names:
                if other_cond != cond:
                    others |= deg_sets[other_cond]
            results[cond] = deg_sets[cond] - others

    elif operation == 'shared':
        # Intersection of all
        shared = deg_sets[condition_names[0]]
        for cond in condition_names[1:]:
            shared = shared & deg_sets[cond]
        results['shared'] = shared

    elif operation == 'union':
        results['union'] = all_genes

    elif operation == 'venn':
        # All combinations
        from itertools import combinations
        for r in range(1, len(condition_names) + 1):
            for combo in combinations(condition_names, r):
                label = ' & '.join(combo)
                intersection = deg_sets[combo[0]]
                for cond in combo[1:]:
                    intersection = intersection & deg_sets[cond]
                # Remove genes that appear in conditions not in this combo
                others = [c for c in condition_names if c not in combo]
                for other in others:
                    intersection = intersection - deg_sets[other]
                results[label] = intersection

    return results
```

## Direction-Concordant DEGs

```python
def find_concordant_degs(results_A, results_B, padj_threshold=0.05):
    """Find genes DE in same direction in both comparisons."""
    # Both significant
    sig_A = results_A[results_A['padj'] < padj_threshold].index
    sig_B = results_B[results_B['padj'] < padj_threshold].index
    common = set(sig_A) & set(sig_B)

    # Same direction
    concordant = []
    for gene in common:
        lfc_A = results_A.loc[gene, 'log2FoldChange']
        lfc_B = results_B.loc[gene, 'log2FoldChange']
        if (lfc_A > 0 and lfc_B > 0) or (lfc_A < 0 and lfc_B < 0):
            concordant.append(gene)

    return concordant
```

## Filter by Gene List

```python
# Filter to specific genes of interest
genes_of_interest = ['TP53', 'BRCA1', 'EGFR', 'MYC']
results_filtered = results.loc[results.index.intersection(genes_of_interest)]

# Filter to genes in a pathway
pathway_genes = ['GENE1', 'GENE2', 'GENE3']  # From pathway database
pathway_results = results.loc[results.index.intersection(pathway_genes)]
```

## Rank Genes

```python
# Rank by combined metric: -log10(padj) * sign(log2FC)
results['rank_metric'] = -np.log10(results['padj']) * np.sign(results['log2FoldChange'])
results_ranked = results.sort_values('rank_metric', ascending=False)

# Alternative: Use stat column (Wald statistic)
results_ranked = results.sort_values('stat', ascending=False)
```

## Export Filtered Results

```python
# Export significant DEGs
sig_genes = filter_degs(results, padj_threshold=0.05, lfc_threshold=0.5)
sig_genes.to_csv('significant_degs.csv')

# Export top genes
top_genes = results.sort_values('padj').head(100)
top_genes.to_csv('top_100_degs.csv')

# Export gene list only
gene_list = sig_genes.index.tolist()
with open('gene_list.txt', 'w') as f:
    f.write('\n'.join(gene_list))
```

## Summary Statistics

```python
def summarize_results(results, padj_threshold=0.05, lfc_threshold=0):
    """Generate summary statistics for DESeq2 results."""
    sig = results[
        (results['padj'] < padj_threshold) &
        (results['log2FoldChange'].abs() > lfc_threshold)
    ]

    summary = {
        'total_genes': len(results),
        'genes_with_padj': len(results.dropna(subset=['padj'])),
        'significant_genes': len(sig),
        'upregulated': len(sig[sig['log2FoldChange'] > 0]),
        'downregulated': len(sig[sig['log2FoldChange'] < 0]),
        'mean_lfc_up': sig[sig['log2FoldChange'] > 0]['log2FoldChange'].mean(),
        'mean_lfc_down': sig[sig['log2FoldChange'] < 0]['log2FoldChange'].mean(),
        'max_lfc': sig['log2FoldChange'].max(),
        'min_lfc': sig['log2FoldChange'].min(),
        'median_basemean': sig['baseMean'].median()
    }

    return summary
```

## Complex Filtering Example

```python
# Multi-criteria filtering for publication-ready DEG list
def get_publication_degs(results):
    """Filter for high-confidence, biologically meaningful DEGs."""
    filtered = results[
        (results['padj'] < 0.01) &  # Stringent significance
        (results['log2FoldChange'].abs() > 1) &  # 2-fold change
        (results['baseMean'] > 50) &  # Adequate expression
        (results['lfcSE'] < 0.5)  # Reasonable SE
    ].copy()

    # Remove outliers (very high LFC might be technical artifacts)
    lfc_upper = filtered['log2FoldChange'].quantile(0.95)
    lfc_lower = filtered['log2FoldChange'].quantile(0.05)
    filtered = filtered[
        (filtered['log2FoldChange'] <= lfc_upper) &
        (filtered['log2FoldChange'] >= lfc_lower)
    ]

    # Sort by combined metric
    filtered['score'] = -np.log10(filtered['padj']) * filtered['log2FoldChange'].abs()
    filtered = filtered.sort_values('score', ascending=False)

    return filtered
```

## Example: Multi-Condition Analysis

```python
# Compare 3 conditions to control
conditions = ['A', 'B', 'C']
all_results = {}

for cond in conditions:
    stat_res = DeseqStats(dds, contrast=['condition', cond, 'control'], quiet=True)
    stat_res.run_wald_test()
    all_results[cond] = stat_res.results_df

# Get DEG sets
deg_sets = {
    cond: set(all_results[cond][all_results[cond]['padj'] < 0.05].index)
    for cond in conditions
}

# Find unique and shared DEGs
comparison = compare_deg_sets(deg_sets, operation='unique')
print(f"Unique to A: {len(comparison['A'])}")
print(f"Unique to B: {len(comparison['B'])}")
print(f"Unique to C: {len(comparison['C'])}")

shared = compare_deg_sets(deg_sets, operation='shared')
print(f"Shared across all: {len(shared['shared'])}")
```
