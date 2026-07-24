# Seurat to Scanpy Translation

Quick reference for Seurat (R) users transitioning to Scanpy (Python).

---

## Seurat vs Scanpy Equivalents

| Operation | Seurat (R) | Scanpy (Python) |
|-----------|------------|-----------------|
| Load 10X | `Read10X()` | `sc.read_10x_mtx()` |
| Create object | `CreateSeuratObject()` | `ad.AnnData()` |
| Normalize | `NormalizeData()` | `sc.pp.normalize_total() + sc.pp.log1p()` |
| Find HVGs | `FindVariableFeatures()` | `sc.pp.highly_variable_genes()` |
| Scale | `ScaleData()` | `sc.pp.scale()` |
| PCA | `RunPCA()` | `sc.tl.pca()` |
| Find neighbors | `FindNeighbors()` | `sc.pp.neighbors()` |
| Cluster | `FindClusters()` | `sc.tl.leiden()` |
| UMAP | `RunUMAP()` | `sc.tl.umap()` |
| t-SNE | `RunTSNE()` | `sc.tl.tsne()` |
| Find markers | `FindMarkers()` | `sc.tl.rank_genes_groups()` |
| DE test | `FindMarkers(test.use="wilcox")` | `method='wilcoxon'` |
| Subset | `subset(seurat, subset = ...)` | `adata[adata.obs['col'] == val]` |
| Batch correction | `RunHarmony()` | `harmonypy.run_harmony()` |

---

## Side-by-Side Workflows

### Seurat (R)
```r
library(Seurat)

# Load and create object
data <- Read10X("filtered_gene_bc_matrices/hg19/")
seurat <- CreateSeuratObject(counts = data, min.cells = 3, min.features = 200)

# QC
seurat[["percent.mt"]] <- PercentageFeatureSet(seurat, pattern = "^MT-")
seurat <- subset(seurat, subset = percent.mt < 20)

# Normalize
seurat <- NormalizeData(seurat)
seurat <- FindVariableFeatures(seurat, nfeatures = 2000)
seurat <- ScaleData(seurat)

# PCA
seurat <- RunPCA(seurat, npcs = 50)

# Cluster
seurat <- FindNeighbors(seurat, dims = 1:30)
seurat <- FindClusters(seurat, resolution = 0.5)
seurat <- RunUMAP(seurat, dims = 1:30)

# Find markers
markers <- FindMarkers(seurat, ident.1 = 0, ident.2 = 1)
```

### Scanpy (Python)
```python
import scanpy as sc

# Load
adata = sc.read_10x_mtx("filtered_gene_bc_matrices/hg19/")

# QC
adata.var['mt'] = adata.var_names.str.startswith('MT-')
sc.pp.calculate_qc_metrics(adata, qc_vars=['mt'], inplace=True)
adata = adata[adata.obs['pct_counts_mt'] < 20].copy()
sc.pp.filter_cells(adata, min_genes=200)
sc.pp.filter_genes(adata, min_cells=3)

# Normalize
sc.pp.normalize_total(adata, target_sum=1e4)
sc.pp.log1p(adata)

# HVG + Scale
sc.pp.highly_variable_genes(adata, n_top_genes=2000)
sc.pp.scale(adata, max_value=10)

# PCA
sc.tl.pca(adata, n_comps=50)

# Cluster
sc.pp.neighbors(adata, n_pcs=30)
sc.tl.leiden(adata, resolution=0.5)
sc.tl.umap(adata)

# Find markers
sc.tl.rank_genes_groups(adata, groupby='leiden', method='wilcoxon')
markers_0 = sc.get.rank_genes_groups_df(adata, group='0')
```

---

## Key Differences

### 1. Data Structure
- **Seurat**: Seurat object with `@data`, `@meta.data`, `@reductions`
- **Scanpy**: AnnData object with `.X`, `.obs`, `.var`, `.obsm`, `.varm`

### 2. Normalization
- **Seurat**: `NormalizeData()` does log-normalization in one step
- **Scanpy**: Two steps: `normalize_total()` then `log1p()`

### 3. Clustering
- **Seurat**: Louvain algorithm via `FindClusters()`
- **Scanpy**: Leiden (recommended) or Louvain via `sc.tl.leiden()` or `sc.tl.louvain()`

### 4. Subsetting
- **Seurat**: `subset(seurat, subset = cell_type == "T cells")`
- **Scanpy**: `adata[adata.obs['cell_type'] == 'T cells']`

### 5. Metadata
- **Seurat**: `seurat@meta.data$new_column <- values`
- **Scanpy**: `adata.obs['new_column'] = values`

---

## Converting Between Formats

### Seurat to AnnData
```python
import scanpy as sc

# Save from R
# saveRDS(seurat, "seurat.rds")

# Load in Python (requires rpy2)
import anndata2ri
anndata2ri.activate()

from rpy2.robjects import r
r('library(Seurat)')
r('seurat <- readRDS("seurat.rds")')
r('SaveH5Seurat(seurat, "seurat.h5seurat")')
r('Convert("seurat.h5seurat", "h5ad")')

adata = sc.read_h5ad("seurat.h5ad")
```

### AnnData to Seurat
```python
# Save from Python
adata.write_h5ad("adata.h5ad")

# Load in R
library(SeuratDisk)
Convert("adata.h5ad", "seurat.h5seurat")
seurat <- LoadH5Seurat("seurat.h5seurat")
```

---

## When to Use Each

### Use Seurat (R) when:
- Working in R ecosystem (Bioconductor, ggplot2)
- Using Seurat-specific methods (SCTransform, CCA integration)
- Team uses R

### Use Scanpy (Python) when:
- Working in Python ecosystem (pandas, scikit-learn, PyTorch)
- Need integration with ML pipelines
- Large datasets (Scanpy generally faster)
- Prefer Leiden clustering

---

## See Also

- **scanpy_workflow.md** - Full Scanpy pipeline
- **clustering_guide.md** - Leiden vs Louvain
