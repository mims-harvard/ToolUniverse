# Trajectory Inference and Pseudotime Analysis

Guide to trajectory analysis and pseudotime ordering in single-cell data.

---

## Overview

Trajectory analysis orders cells along a developmental or temporal continuum (pseudotime). Use for:
- Differentiation studies (stem cells → mature cells)
- Cell cycle analysis
- Response to stimulation over time
- Disease progression

---

## Diffusion Pseudotime (DPT)

Built into scanpy, based on diffusion maps.

```python
import scanpy as sc

# After standard preprocessing and clustering
# 1. Identify root cell (start of trajectory)
adata.uns['iroot'] = np.flatnonzero(
    adata.obs['leiden'] == '0'  # Choose starting cluster
)[0]

# 2. Compute diffusion map
sc.tl.diffmap(adata)

# 3. Compute DPT
sc.tl.dpt(adata)

# 4. Visualize
sc.pl.umap(adata, color=['dpt_pseudotime', 'leiden'])

# Pseudotime values in: adata.obs['dpt_pseudotime']
```

---

## PAGA (Partition-based Graph Abstraction)

Models trajectories as cluster connectivity graph.

```python
# After clustering
sc.tl.paga(adata, groups='leiden')

# Plot PAGA graph
sc.pl.paga(adata, color='leiden')

# Initialize UMAP positions from PAGA
sc.tl.umap(adata, init_pos='paga')

# Plot trajectory
sc.pl.umap(adata, color=['leiden', 'CD34'])  # Stem cell marker
```

---

## Gene Expression Along Pseudotime

```python
# Genes that change along pseudotime
sc.tl.rank_genes_groups(adata, groupby='leiden', method='wilcoxon')

# Plot gene expression vs pseudotime
import matplotlib.pyplot as plt

genes_of_interest = ['CD34', 'CD38', 'CD14']
for gene in genes_of_interest:
    if gene in adata.var_names:
        plt.figure()
        plt.scatter(
            adata.obs['dpt_pseudotime'],
            adata[:, gene].X.toarray().flatten(),
            alpha=0.3, s=5
        )
        plt.xlabel('Pseudotime')
        plt.ylabel(f'{gene} expression')
        plt.title(f'{gene} along trajectory')
        plt.show()
```

---

## External Tools

### PAGA with RNA velocity (scVelo)
```python
import scvelo as scv

# Compute RNA velocity
scv.pp.filter_and_normalize(adata)
scv.pp.moments(adata)
scv.tl.velocity(adata)
scv.tl.velocity_graph(adata)

# Visualize
scv.pl.velocity_embedding_stream(adata, basis='umap')
```

### Monocle-style (via Python wrapper)
```python
# Not native to scanpy, requires specialized packages
# For Monocle analysis, consider using R/Seurat integration
```

---

## Tips

1. **Root cell selection**: Critical for pseudotime. Choose starting cell type.
2. **Linear vs branched**: DPT handles linear trajectories, PAGA handles branching.
3. **Validation**: Check marker gene expression matches biological expectation.
4. **Multiple trajectories**: For complex differentiation, use PAGA.

---

## See Also

- **scanpy_workflow.md** - Preprocessing before trajectory
- **clustering_guide.md** - Clustering for PAGA
