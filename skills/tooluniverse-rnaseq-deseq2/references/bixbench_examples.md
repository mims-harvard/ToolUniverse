# BixBench Question Patterns

All 10 common question patterns with examples from BixBench validation.

## Pattern 1: Basic DEG Count

**Question**: "How many genes show significant DE (padj < 0.05, |log2FC| > 0.5)?"

**Code**:
```python
degs = results[
    (results['padj'] < 0.05) &
    (results['log2FoldChange'].abs() > 0.5)
]
answer = len(degs)
```

**Variations**:
- "How many differentially expressed genes?"
- "Number of significant genes"
- "Count of DEGs with adjusted p-value < 0.01"

---

## Pattern 2: Specific Gene Value

**Question**: "What is the log2FC of gene X?"

**Code**:
```python
answer = round(results.loc['GENE_X', 'log2FoldChange'], 2)
```

**Handling missing genes**:
```python
def get_gene_result(results_df, gene_name, column='log2FoldChange'):
    """Get value with case-insensitive matching."""
    # Try exact match first
    if gene_name in results_df.index:
        return results_df.loc[gene_name, column]

    # Case-insensitive match
    idx_lower = {g.lower(): g for g in results_df.index}
    if gene_name.lower() in idx_lower:
        actual_name = idx_lower[gene_name.lower()]
        return results_df.loc[actual_name, column]

    # Partial match
    matches = [g for g in results_df.index if gene_name.lower() in g.lower()]
    if len(matches) == 1:
        return results_df.loc[matches[0], column]

    return None  # Gene not found

answer = round(get_gene_result(results, "TP53", "log2FoldChange"), 2)
```

**Variations**:
- "What is the padj for gene Y?"
- "What is the baseMean of gene Z?"
- "What is the p-value for gene ABC?"

---

## Pattern 3: Direction-Specific DEGs

**Question**: "How many genes are upregulated?"

**Code**:
```python
up_degs = results[
    (results['padj'] < 0.05) &
    (results['log2FoldChange'] > 0)
]
answer = len(up_degs)
```

**Downregulated**:
```python
down_degs = results[
    (results['padj'] < 0.05) &
    (results['log2FoldChange'] < 0)
]
answer = len(down_degs)
```

**With LFC threshold**:
```python
up_degs = results[
    (results['padj'] < 0.05) &
    (results['log2FoldChange'] > 0.5)  # Threshold
]
answer = len(up_degs)
```

---

## Pattern 4: Multi-Condition Comparison (Set Operations)

**Question**: "How many genes are uniquely DE in condition A but not B or C?"

**Code**:
```python
# Extract DEG sets for each condition
degs_A = set(results_A[results_A['padj'] < 0.05].index)
degs_B = set(results_B[results_B['padj'] < 0.05].index)
degs_C = set(results_C[results_C['padj'] < 0.05].index)

# Unique to A
unique_A = degs_A - degs_B - degs_C
answer = len(unique_A)
```

**Shared across all**:
```python
shared = degs_A & degs_B & degs_C
answer = len(shared)
```

**Percentage overlap**:
```python
overlap = degs_A & degs_B
percentage = round(len(overlap) / len(degs_A) * 100, 1)
```

**Compare two sets**:
```python
def compare_deg_sets(deg_sets, operation='unique'):
    """Compare DEG sets across conditions."""
    results = {}
    condition_names = list(deg_sets.keys())

    if operation == 'unique':
        # Genes unique to each condition
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

    return results

# Usage
deg_sets = {
    'A': set(results_A[results_A['padj'] < 0.05].index),
    'B': set(results_B[results_B['padj'] < 0.05].index),
    'C': set(results_C[results_C['padj'] < 0.05].index)
}
unique = compare_deg_sets(deg_sets, operation='unique')
answer = len(unique['A'])
```

---

## Pattern 5: Dispersion Count

**Question**: "How many genes have dispersion below 1e-5 prior to fitting?"

**Code**:
```python
genewise = dds.var['genewise_dispersions']
answer = (genewise < 1e-5).sum()
```

**After shrinkage**:
```python
map_disp = dds.var['MAP_dispersions']
answer = (map_disp < 1e-5).sum()
```

**Dispersion diagnostics**:
```python
def dispersion_diagnostics(dds, threshold=1e-5):
    """Analyze dispersion estimates."""
    diag = {}

    if 'genewise_dispersions' in dds.var.columns:
        gwd = dds.var['genewise_dispersions']
        diag['genewise_below_threshold'] = (gwd < threshold).sum()
        diag['genewise_min'] = gwd.min()
        diag['genewise_max'] = gwd.max()
        diag['genewise_median'] = gwd.median()

    if 'MAP_dispersions' in dds.var.columns:
        mapd = dds.var['MAP_dispersions']
        diag['MAP_below_threshold'] = (mapd < threshold).sum()

    return diag

# Usage
diag = dispersion_diagnostics(dds, threshold=1e-5)
answer = diag['genewise_below_threshold']
```

---

## Pattern 6: DEGs + Enrichment

**Question**: "What is the adjusted p-value for pathway X in enrichment of DEGs?"

**Code**:
```python
import gseapy as gp

# Get DEGs
degs = results[
    (results['padj'] < 0.05) &
    (results['log2FoldChange'].abs() > 0.5)
]
gene_list = degs.index.tolist()

# Run enrichment
enr = gp.enrich(
    gene_list=gene_list,
    gene_sets='KEGG_2021_Human',
    outdir=None,
    no_plot=True,
    verbose=False
)

# Extract answer
pathway = enr.results[enr.results['Term'].str.contains('ABC transporters')]
answer = round(pathway.iloc[0]['Adjusted P-value'], 4)
```

**Count significant pathways**:
```python
answer = len(enr.results[enr.results['Adjusted P-value'] < 0.05])
```

**Gene count in pathway**:
```python
pathway = enr.results[enr.results['Term'].str.contains('ribosome')]
overlap = pathway.iloc[0]['Overlap']  # e.g., "25/150"
answer = int(overlap.split('/')[0])  # 25
```

---

## Pattern 7: Percentage Calculation

**Question**: "What percentage of DE genes in A are also DE in B?"

**Code**:
```python
degs_A = set(results_A[results_A['padj'] < 0.05].index)
degs_B = set(results_B[results_B['padj'] < 0.05].index)
overlap = degs_A & degs_B
percentage = round(len(overlap) / len(degs_A) * 100, 1)
```

**Percentage upregulated**:
```python
all_degs = results[results['padj'] < 0.05]
up_degs = all_degs[all_degs['log2FoldChange'] > 0]
percentage = round(len(up_degs) / len(all_degs) * 100, 1)
```

---

## Pattern 8: Wilson Confidence Interval

**Question**: "What is the 95% CI for the proportion of DEGs using Wilson method?"

**Code**:
```python
from statsmodels.stats.proportion import proportion_confint

n_total = len(results.dropna(subset=['padj']))
n_sig = len(results[(results['padj'] < 0.05) & (results['log2FoldChange'].abs() > 1)])

ci_low, ci_high = proportion_confint(n_sig, n_total, method='wilson')
answer = (round(ci_low, 2), round(ci_high, 2))
```

**Other CI methods**:
```python
# Normal approximation
ci_low, ci_high = proportion_confint(n_sig, n_total, method='normal')

# Clopper-Pearson (exact)
ci_low, ci_high = proportion_confint(n_sig, n_total, method='beta')
```

---

## Pattern 9: Enrichment Gene Count in Pathway

**Question**: "How many DEGs contribute to pathway X enrichment?"

**Code**:
```python
import gseapy as gp

# Run enrichment
degs = results[(results['padj'] < 0.05)]
gene_list = degs.index.tolist()
enr = gp.enrich(gene_list=gene_list, gene_sets='KEGG_2021_Human')

# Find pathway
pathway_row = enr.results[enr.results['Term'].str.contains('ABC transporters')].iloc[0]

# Extract gene count
overlap_str = pathway_row['Overlap']  # e.g., "11/42"
n_genes = int(overlap_str.split('/')[0])  # 11

# Or get gene list
genes_in_pathway = pathway_row['Genes'].split(';')
answer = len(genes_in_pathway)
```

---

## Pattern 10: Batch Effect Assessment

**Question**: "How does removing batch-affected samples change DEG count?"

**Code**:
```python
# Run with all samples
dds_all = DeseqDataSet(counts=counts_all, metadata=metadata_all, design="~condition", quiet=True)
dds_all.deseq2()
stat_res_all = DeseqStats(dds_all, contrast=['condition', 'treatment', 'control'], quiet=True)
stat_res_all.run_wald_test()
results_all = stat_res_all.results_df
n_all = len(results_all[(results_all['padj'] < 0.05) & (results_all['log2FoldChange'].abs() > 1)])

# Run without batch-affected samples
counts_clean = counts_all.loc[~metadata_all['batch_affected']]
metadata_clean = metadata_all[~metadata_all['batch_affected']]
dds_clean = DeseqDataSet(counts=counts_clean, metadata=metadata_clean, design="~condition", quiet=True)
dds_clean.deseq2()
stat_res_clean = DeseqStats(dds_clean, contrast=['condition', 'treatment', 'control'], quiet=True)
stat_res_clean.run_wald_test()
results_clean = stat_res_clean.results_df
n_clean = len(results_clean[(results_clean['padj'] < 0.05) & (results_clean['log2FoldChange'].abs() > 1)])

# Compare
if n_clean > n_all:
    answer = "Increases the number of differentially expressed genes"
else:
    answer = "Decreases the number of differentially expressed genes"
```

---

## Additional Patterns

### Multiple Testing Correction Comparison

**Question**: "How many genes are significant with Bonferroni vs BH correction?"

```python
from statsmodels.stats.multitest import multipletests
import numpy as np

pvalues = results['pvalue'].values
mask = ~np.isnan(pvalues)

# Benjamini-Hochberg (default)
_, padj_bh, _, _ = multipletests(pvalues[mask], method='fdr_bh')
n_bh = (padj_bh < 0.05).sum()

# Bonferroni
_, padj_bonf, _, _ = multipletests(pvalues[mask], method='bonferroni')
n_bonf = (padj_bonf < 0.05).sum()

answer = f"BH: {n_bh}, Bonferroni: {n_bonf}"
```

### Protein-Coding vs Non-Coding

**Question**: "Compare DE between protein-coding and non-protein-coding genes"

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

# Classify genes
def classify_genes(gene_list, tu):
    """Classify genes as protein-coding or non-protein-coding."""
    classifications = {}
    for gene in gene_list:
        try:
            result = tu.tools.MyGene_query_genes(query=gene)
            if isinstance(result, list) and len(result) > 0:
                gene_type = result[0].get('type_of_gene', 'unknown')
                classifications[gene] = gene_type
        except Exception:
            classifications[gene] = 'unknown'
    return classifications

# Get DEGs
degs = results[results['padj'] < 0.05].index.tolist()
gene_types = classify_genes(degs, tu)

# Count by type
from collections import Counter
type_counts = Counter(gene_types.values())
n_protein_coding = type_counts.get('protein-coding', 0)
n_non_coding = sum(v for k, v in type_counts.items() if k != 'protein-coding' and k != 'unknown')

answer = f"Protein-coding: {n_protein_coding}, Non-coding: {n_non_coding}"
```

### miRNA Analysis

**Question**: "Differential expression of miRNA data"

```python
from scipy import stats

def mirna_de_analysis(expression_df, groups):
    """Simple DE for pre-normalized miRNA data."""
    group_labels = expression_df.index.map(groups)
    unique_groups = group_labels.unique()

    g1 = expression_df[group_labels == unique_groups[0]]
    g2 = expression_df[group_labels == unique_groups[1]]

    results_list = []
    for gene in expression_df.columns:
        stat, pval = stats.ttest_ind(g1[gene].dropna(), g2[gene].dropna())
        lfc = np.log2(g2[gene].mean() / g1[gene].mean()) if g1[gene].mean() > 0 else np.nan
        results_list.append({
            'gene': gene,
            'log2FoldChange': lfc,
            'pvalue': pval,
            'stat': stat
        })

    results_df = pd.DataFrame(results_list).set_index('gene')

    # Multiple testing correction
    from statsmodels.stats.multitest import multipletests
    mask = ~results_df['pvalue'].isna()
    _, results_df.loc[mask, 'padj'], _, _ = multipletests(
        results_df.loc[mask, 'pvalue'], method='fdr_bh'
    )

    return results_df

# Usage
groups = {'sample1': 'control', 'sample2': 'control', 'sample3': 'treated', 'sample4': 'treated'}
results_mirna = mirna_de_analysis(mirna_expression, groups)
n_sig = len(results_mirna[results_mirna['padj'] < 0.05])
```
