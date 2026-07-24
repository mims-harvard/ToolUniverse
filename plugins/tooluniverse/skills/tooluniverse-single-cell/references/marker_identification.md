# Marker Gene Identification and Cell Type Annotation

Guide to finding marker genes and annotating cell types in single-cell data.

---

## Find Marker Genes for Clusters

```python
import scanpy as sc

# Run DE for all clusters
sc.tl.rank_genes_groups(
    adata,
    groupby='leiden',
    method='wilcoxon',  # or 't-test', 'logreg'
    n_genes=100,
    corr_method='benjamini-hochberg'
)

# Get results for cluster 0
markers_0 = sc.get.rank_genes_groups_df(adata, group='0')
print(markers_0.head(10))
```

**Available methods**:
- `wilcoxon`: Non-parametric, robust (default)
- `t-test`: Fast, parametric
- `logreg`: Logistic regression, good for classification

---

## Cell Type Annotation Strategies

### 1. Known Marker Genes

```python
# Define markers for cell types
marker_genes = {
    'T cells': ['CD3D', 'CD3E', 'CD8A', 'CD4'],
    'CD4 T cells': ['CD3D', 'CD4', 'IL7R'],
    'CD8 T cells': ['CD3D', 'CD8A', 'CD8B'],
    'B cells': ['CD19', 'MS4A1', 'CD79A'],
    'Monocytes': ['CD14', 'LYZ', 'S100A9'],
    'CD14 Monocytes': ['CD14', 'LYZ'],
    'CD16 Monocytes': ['FCGR3A', 'MS4A7'],
    'NK cells': ['NKG7', 'GNLY', 'KLRB1'],
    'Dendritic cells': ['FCER1A', 'CD1C'],
}

# Score clusters
from scipy.sparse import issparse
X = adata.X.toarray() if issparse(adata.X) else adata.X
expr_df = pd.DataFrame(X, index=adata.obs_names, columns=adata.var_names)

cluster_scores = {}
for ct, markers in marker_genes.items():
    available = [m for m in markers if m in adata.var_names]
    if available:
        scores = expr_df[available].mean(axis=1)
        cluster_scores[ct] = scores.groupby(adata.obs['leiden']).mean()

# Assign cell types
score_df = pd.DataFrame(cluster_scores)
assignments = score_df.idxmax(axis=1)
adata.obs['cell_type'] = adata.obs['leiden'].map(assignments)
```

### 2. ToolUniverse HPA Database

```python
from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()

# Search for cell-type markers
result = tu.tools.HPA_search_genes_by_query(query="T cell marker blood")
if result:
    print("HPA T cell markers:", [g.get('gene_name') for g in result[:10]])

# Get tissue-specific expression
result = tu.tools.HPA_get_rna_expression_in_specific_tissues(
    ensembl_id="ENSG00000167286",  # CD3D
    tissue_name="blood"
)
```

### 3. Automated Annotation (scanpy)

```python
# Using marker gene scores
sc.tl.marker_gene_overlap(adata, marker_genes)

# Using cell type prediction (if reference available)
import scanpy.external as sce
# sce.tl.ingest(adata, adata_ref, obs='cell_type')
```

---

## Visualize Marker Expression

```python
# Dot plot
sc.pl.dotplot(adata, marker_genes, groupby='leiden')

# Stacked violin
sc.pl.stacked_violin(adata, marker_genes, groupby='leiden')

# UMAP with marker overlay
sc.pl.umap(adata, color=['leiden', 'CD3D', 'CD79A', 'CD14'])
```

---

## Validate Annotations

### Check Marker Specificity
```python
# Calculate marker specificity
for ct in adata.obs['cell_type'].unique():
    mask = adata.obs['cell_type'] == ct
    markers_for_ct = marker_genes.get(ct, [])

    for marker in markers_for_ct:
        if marker in adata.var_names:
            expr_in_ct = adata[mask, marker].X.mean()
            expr_out_ct = adata[~mask, marker].X.mean()
            fold_enrichment = expr_in_ct / (expr_out_ct + 0.001)
            print(f"{ct} - {marker}: {fold_enrichment:.2f}x enriched")
```

### Cross-Reference with Literature
```python
# Get top expressed genes in cell type
ct_data = adata[adata.obs['cell_type'] == 'CD4 T cells']
X = ct_data.X.toarray() if issparse(ct_data.X) else ct_data.X
mean_expr = np.mean(X, axis=0)
top_genes = ct_data.var_names[np.argsort(mean_expr)[::-1][:20]]
print(f"Top genes in CD4 T cells: {list(top_genes)}")
```

---

## Common Cell Type Markers

### Immune Cells (PBMC)
```python
immune_markers = {
    'T cells': ['CD3D', 'CD3E', 'CD3G'],
    'CD4 T cells': ['CD3D', 'CD4', 'IL7R', 'TCF7'],
    'CD8 T cells': ['CD3D', 'CD8A', 'CD8B', 'GZMK'],
    'Regulatory T cells': ['FOXP3', 'IL2RA', 'CTLA4'],
    'NK cells': ['NKG7', 'GNLY', 'KLRD1', 'KLRB1'],
    'B cells': ['CD19', 'MS4A1', 'CD79A', 'CD79B'],
    'Plasma cells': ['IGHG1', 'MZB1', 'SDC1', 'XBP1'],
    'Monocytes': ['CD14', 'LYZ', 'S100A9', 'S100A8'],
    'CD14 Monocytes': ['CD14', 'LYZ', 'FCN1'],
    'CD16 Monocytes': ['FCGR3A', 'MS4A7', 'CDKN1C'],
    'Dendritic cells': ['FCER1A', 'CD1C', 'CLEC10A'],
    'pDC': ['IL3RA', 'GZMB', 'SERPINF1', 'ITM2C'],
    'Platelets': ['PPBP', 'PF4', 'TUBB1'],
}
```

### Tumor Microenvironment
```python
tme_markers = {
    'Cancer cells': ['EPCAM', 'KRT8', 'KRT18', 'KRT19'],
    'CAFs': ['COL1A1', 'COL1A2', 'DCN', 'ACTA2'],
    'Endothelial': ['PECAM1', 'VWF', 'CDH5'],
    'TAMs': ['CD68', 'CD163', 'MSR1'],
    'Exhausted T cells': ['PDCD1', 'HAVCR2', 'LAG3', 'TIGIT'],
}
```

---

## Tips

1. **Multiple markers**: Use 3-5 markers per cell type for robustness
2. **Negative markers**: Also check genes NOT expressed
3. **Expression levels**: Mean expression matters, not just presence
4. **Subclustering**: For ambiguous clusters, re-cluster at higher resolution
5. **Manual curation**: Always manually review top markers

---

## See Also

- **scanpy_workflow.md** - Clustering before annotation
- **cell_communication.md** - Use annotated cell types for communication
