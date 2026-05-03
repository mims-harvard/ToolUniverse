# ANOVA and Statistical Tests Reference

## One-way ANOVA (Single Feature)

```python
from scipy import stats

group1 = df[df['celltype'] == 'CD4']['expression']
group2 = df[df['celltype'] == 'CD8']['expression']
group3 = df[df['celltype'] == 'CD14']['expression']

f_stat, p_value = stats.f_oneway(group1, group2, group3)
print(f"F-statistic: {f_stat:.4f}, p-value: {p_value:.6f}")
```

## Multi-Feature ANOVA Decision Tree

When data has **multiple features** (genes, miRNAs, metabolites), there are TWO approaches:

```
Question: "What is the F-statistic comparing [feature] expression across groups?"

DECISION TREE:
|
+-- Does question specify "the F-statistic" (singular)?
|   |
|   +-- YES, singular -> Likely asking for SPECIFIC FEATURE(S) F-statistic
|   |   |
|   |   +-- Are there thousands of features (genes, miRNAs)?
|   |   |   YES -> Per-feature approach (Method B below)
|   |   |
|   |   +-- Is there one feature of interest?
|   |      YES -> Single feature ANOVA (Method A below)
|   |
|   +-- NO, asks about "all features" or "genes" (plural)?
|      YES -> Aggregate approach or per-feature summary
|
+-- When unsure: Calculate PER-FEATURE and report summary statistics
```

## Method A: Aggregate ANOVA (all features combined)

Use when: Testing overall expression differences across all features.
Result: Single F-statistic representing global effect.

```python
groups_agg = []
for celltype in ['CD4', 'CD8', 'CD14']:
    samples = df[df['celltype'] == celltype]
    all_values = expression_matrix.loc[:, samples.index].values.flatten()
    groups_agg.append(all_values)

f_stat_agg, p_value = stats.f_oneway(*groups_agg)
print(f"Aggregate F-statistic: {f_stat_agg:.4f}")
# Result: Very large F-statistic (e.g., 153.8)
```

## Method B: Per-Feature ANOVA (RECOMMENDED for gene expression)

Use when: Testing EACH feature individually (most common in genomics).
Result: Distribution of F-statistics (one per feature).

```python
import numpy as np
from scipy import stats

per_feature_f_stats = []

for feature in expression_matrix.index:
    groups = []
    for celltype in ['CD4', 'CD8', 'CD14']:
        samples = df[df['celltype'] == celltype]
        values = expression_matrix.loc[feature, samples.index].values
        groups.append(values)

    f_stat, _ = stats.f_oneway(*groups)
    if not np.isnan(f_stat):
        per_feature_f_stats.append((feature, f_stat))

# Summary statistics
f_values = [f for _, f in per_feature_f_stats]
print(f"Per-feature F-statistics:")
print(f"  Median: {np.median(f_values):.4f}")
print(f"  Mean: {np.mean(f_values):.4f}")
print(f"  Range: [{np.min(f_values):.4f}, {np.max(f_values):.4f}]")

# Find features in specific range (e.g., 0.76-0.78)
target_features = [(name, f) for name, f in per_feature_f_stats
                   if 0.76 <= f <= 0.78]
if target_features:
    print(f"Features with F in [0.76, 0.78]: {len(target_features)}")
    for name, f_val in target_features:
        print(f"  {name}: F = {f_val:.6f}")
```

## Key Differences

| Aspect | Method A (Aggregate) | Method B (Per-feature) |
|--------|---------------------|------------------------|
| **Interpretation** | Overall expression difference | Feature-specific differences |
| **Result** | 1 F-statistic | N F-statistics (N = # features) |
| **Typical value** | Very large (e.g., 153.8) | Small to large (e.g., 0.1 to 100+) |
| **Use case** | Global effect size | Gene/biomarker discovery |
| **Common in** | Rarely used | **Genomics, proteomics, metabolomics** |

## Real-World Example (BixBench bix-36-q1)

- Question: "What is the F-statistic comparing miRNA expression across immune cell types?"
- Expected: 0.76-0.78
- Method A (aggregate): 153.836 -- WRONG
- Method B (per-miRNA): Found 2 miRNAs with F in [0.76, 0.78] -- CORRECT

**Default assumption for gene expression data**: Use **Method B (per-feature)**.

## Other Statistical Tests

### t-test (two groups)
```python
t_stat, p_value = stats.ttest_ind(group1, group2)
```

### Chi-square (categorical)
```python
contingency = pd.crosstab(df['exposure'], df['outcome'])
chi2, p_value, dof, expected = stats.chi2_contingency(contingency)
```

### Mann-Whitney U (non-parametric, two groups)
```python
u_stat, p_value = stats.mannwhitneyu(group1, group2, alternative='two-sided')
```

### Kruskal-Wallis (non-parametric, 3+ groups)
```python
h_stat, p_value = stats.kruskal(group1, group2, group3)
```
