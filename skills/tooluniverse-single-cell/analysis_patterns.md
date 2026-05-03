# Single-Cell Analysis Patterns

Detailed code patterns for common BixBench analysis types.

---

## Pattern 1: Per-Cell-Type Differential Expression

**Question**: "Which immune cell type has the most DEGs after treatment?"
**BixBench**: bix-33

```python
import scanpy as sc

adata = sc.read_h5ad("data.h5ad")
sc.pp.normalize_total(adata, target_sum=1e4)
sc.pp.log1p(adata)

cell_types = adata.obs['cell_type'].unique()
de_results = {}

for ct in cell_types:
    adata_ct = adata[adata.obs['cell_type'] == ct].copy()
    n_treat = (adata_ct.obs['condition'] == 'treatment').sum()
    n_ctrl = (adata_ct.obs['condition'] == 'control').sum()
    if n_treat < 3 or n_ctrl < 3:
        continue

    sc.tl.rank_genes_groups(adata_ct, groupby='condition',
                             groups=['treatment'], reference='control',
                             method='wilcoxon')
    df = sc.get.rank_genes_groups_df(adata_ct, group='treatment')
    sig = df[df['pvals_adj'] < 0.05]
    de_results[ct] = {'n_sig': len(sig), 'results': df}
    print(f"{ct}: {len(sig)} DEGs")

top_ct = max(de_results, key=lambda x: de_results[x]['n_sig'])
print(f"Answer: {top_ct} ({de_results[top_ct]['n_sig']} DEGs)")
```

---

## Pattern 2: Gene Property vs Expression Correlation

**Question**: "What is the Pearson correlation between gene length and expression in CD4 T cells?"
**BixBench**: bix-22

```python
import scanpy as sc
import pandas as pd
import numpy as np
from scipy import stats
from scipy.sparse import issparse

adata = sc.read_h5ad("data.h5ad")
gene_info = pd.read_csv("gene_info.tsv", sep='\t', index_col=0)
common = adata.var_names.intersection(gene_info.index)
adata.var['gene_length'] = gene_info.loc[common, 'gene_length'].reindex(adata.var_names)
adata.var['gene_type'] = gene_info.loc[common, 'gene_type'].reindex(adata.var_names)

mask = adata.var['gene_type'] == 'protein_coding'
adata_pc = adata[:, mask].copy()

cell_types = ['CD4 T cells', 'CD8 T cells', 'CD14 Monocytes']
for ct in cell_types:
    adata_ct = adata_pc[adata_pc.obs['cell_type'] == ct]
    X = adata_ct.X.toarray() if issparse(adata_ct.X) else adata_ct.X
    mean_expr = np.mean(X, axis=0)
    gene_lengths = adata_ct.var['gene_length'].values
    valid = ~np.isnan(gene_lengths) & ~np.isnan(mean_expr)
    r, p = stats.pearsonr(gene_lengths[valid], mean_expr[valid])
    print(f"{ct}: r = {r:.6f}, p = {p:.2e}, n = {valid.sum()} genes")
```

---

## Pattern 3: PCA on Expression Matrix

**Question**: "What percentage of variance is explained by PC1 after log10 transform?"
**BixBench**: bix-27

```python
import pandas as pd
import numpy as np
from sklearn.decomposition import PCA

df = pd.read_csv("expression.csv", index_col=0)
if df.shape[0] > df.shape[1] * 5:
    df = df.T  # Genes were rows, transpose

X = np.log10(df.values + 1)
n_components = min(X.shape[0], X.shape[1])
pca = PCA(n_components=n_components)
pca.fit(X)

print(f"PC1: {pca.explained_variance_ratio_[0]*100:.2f}% variance")
print(f"PC1+PC2: {sum(pca.explained_variance_ratio_[:2])*100:.2f}%")
print(f"Top 10 PCs: {sum(pca.explained_variance_ratio_[:10])*100:.2f}%")
```

---

## Pattern 4: Statistical Comparison Between Cell Types

**Question**: "What is the t-statistic comparing LFCs between CD4/CD8 and other cell types?"
**BixBench**: bix-31

```python
from scipy import stats
import numpy as np

# After running per-cell-type DE (Pattern 1):
cd4_lfc = de_results['CD4 T cells']['results']['log2FoldChange'].values
cd8_lfc = de_results['CD8 T cells']['results']['log2FoldChange'].values
cd4_cd8_lfc = np.concatenate([cd4_lfc, cd8_lfc])

other_lfc = []
for ct in ['CD14 Monocytes', 'NK cells', 'B cells']:
    other_lfc.append(de_results[ct]['results']['log2FoldChange'].values)
other_lfc = np.concatenate(other_lfc)

t_stat, p_val = stats.ttest_ind(cd4_cd8_lfc, other_lfc, equal_var=False)
print(f"t-statistic: {t_stat:.4f}")
print(f"p-value: {p_val:.4e}")
```

---

## Pattern 5: ANOVA Across Cell Types

**Question**: "What is the F-statistic for miRNA expression across immune cell types?"
**BixBench**: bix-36

```python
import pandas as pd
from scipy import stats

df = pd.read_csv("mirna_expr.csv", index_col=0)
meta = pd.read_csv("metadata.csv", index_col=0)

meta_filtered = meta[meta['cell_type'] != 'PBMC']
df_filtered = df[meta_filtered.index]

cell_types = meta_filtered['cell_type'].unique()
groups = {}
for ct in cell_types:
    samples = meta_filtered[meta_filtered['cell_type'] == ct].index
    groups[ct] = df_filtered[samples].values.flatten()

f_stat, p_val = stats.f_oneway(*groups.values())
print(f"F-statistic: {f_stat:.4f}")
print(f"p-value: {p_val:.4e}")
```

---

## Pattern 6: Cell-Cell Communication Analysis

**Question**: "Which ligand-receptor interactions are strongest between tumor and T cells?"

```python
from tooluniverse import ToolUniverse
import pandas as pd

tu = ToolUniverse()
tu.load_tools()

# Step 1: Get ligand-receptor pairs from OmniPath
result = tu.run_tool(
    "OmniPath_get_ligand_receptor_interactions",
    databases="CellPhoneDB,CellChatDB"
)
lr_pairs = pd.DataFrame(result['data']['interactions'])

# Step 2: Filter to expressed pairs
expressed_lr = lr_pairs[
    lr_pairs['source_genesymbol'].isin(adata.var_names) &
    lr_pairs['target_genesymbol'].isin(adata.var_names)
]

# Step 3: Score communication between cell types
communication_scores = score_cell_communication(
    adata, expressed_lr, cell_type_col='cell_type'
)

# Step 4: Filter to tumor-T cell interactions
tumor_tcell = communication_scores[
    ((communication_scores['sender'] == 'Tumor') &
     (communication_scores['receiver'].str.contains('T cell'))) |
    ((communication_scores['receiver'] == 'Tumor') &
     (communication_scores['sender'].str.contains('T cell')))
]

top_interactions = tumor_tcell.nlargest(20, 'score')
print(top_interactions[['sender', 'receiver', 'ligand', 'receptor', 'score']])
```

See: references/cell_communication.md for complete helper functions and scoring workflow.

---

## Report Generation

Always extract the specific answer to the user's question:

```python
report = f"""
# Analysis Results

## Per-Cell-Type Differential Expression

| Cell Type | Significant DEGs (padj < 0.05) |
|-----------|-------------------------------|
{chr(10).join([f"| {ct} | {res['n_sig']} |" for ct, res in de_results.items()])}

## Answer

**{top_ct}** has the highest number of significantly differentially expressed
genes with **{de_results[top_ct]['n_sig']} DEGs** (Wilcoxon test, BH-corrected
p < 0.05).
"""
```
