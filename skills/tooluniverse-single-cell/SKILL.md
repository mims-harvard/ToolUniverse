---
name: tooluniverse-single-cell
description: "Production-ready single-cell and expression matrix analysis using scanpy, anndata, and scipy. Performs scRNA-seq QC, normalization, PCA, UMAP, Leiden/Louvain clustering, differential expression (Wilcoxon, t-test, DESeq2), cell type annotation, per-cell-type statistical analysis, gene-expression correlation, batch correction (Harmony), trajectory inference, and cell-cell communication analysis. NEW: Analyzes ligand-receptor interactions between cell types using OmniPath (CellPhoneDB, CellChatDB), scores communication strength, identifies signaling cascades, and handles multi-subunit receptor complexes. Integrates with ToolUniverse gene annotation tools (HPA, Ensembl, MyGene, UniProt) and enrichment tools (gseapy, PANTHER, STRING). Supports h5ad, 10X, CSV/TSV count matrices, and pre-annotated datasets. Use when analyzing single-cell RNA-seq data, studying cell-cell interactions, performing cell type differential expression, computing gene-expression correlations by cell type, analyzing tumor-immune communication, or answering questions about scRNA-seq datasets."
---

# Single-Cell Genomics and Expression Matrix Analysis

Comprehensive single-cell RNA-seq analysis and expression matrix processing using scanpy, anndata, scipy, and ToolUniverse.

---

## When to Use This Skill

Apply when users:
- Have scRNA-seq data (h5ad, 10X, CSV count matrices) and want analysis
- Ask about cell type identification, clustering, or annotation
- Need differential expression analysis by cell type or condition
- Want gene-expression correlation analysis (e.g., gene length vs expression by cell type)
- Ask about PCA, UMAP, t-SNE for expression data
- Need Leiden/Louvain clustering on expression matrices
- Want statistical comparisons between cell types (t-test, ANOVA, fold change)
- Ask about marker genes, batch correction, trajectory, or cell-cell communication

**BixBench Coverage**: 18+ questions across 5 projects (bix-22, bix-27, bix-31, bix-33, bix-36)

**NOT for** (use other skills instead):
- Bulk RNA-seq DESeq2 only -> `tooluniverse-rnaseq-deseq2`
- Gene enrichment only -> `tooluniverse-gene-enrichment`
- VCF/variant analysis -> `tooluniverse-variant-analysis`

---

## Core Principles

1. **Data-first** - Load, inspect, validate before analysis
2. **AnnData-centric** - All data flows through anndata objects
3. **Cell type awareness** - Per-cell-type subsetting when needed
4. **Statistical rigor** - Normalization, multiple testing correction, effect sizes
5. **Question-driven** - Parse what the user is actually asking

---

## Required Packages

```python
import scanpy as sc, anndata as ad, pandas as pd, numpy as np
from scipy import stats
from scipy.cluster.hierarchy import linkage, fcluster
from sklearn.decomposition import PCA
from statsmodels.stats.multitest import multipletests
import gseapy as gp  # enrichment
import harmonypy     # batch correction (optional)
```

Install: `pip install scanpy anndata leidenalg umap-learn harmonypy gseapy pandas numpy scipy scikit-learn statsmodels`

---

## Workflow Decision Tree

```
START: User question about scRNA-seq data
|
+-- FULL PIPELINE (raw counts -> annotated clusters)
|   Workflow: QC -> Normalize -> HVG -> PCA -> Cluster -> Annotate -> DE
|   See: references/scanpy_workflow.md
|
+-- DIFFERENTIAL EXPRESSION (per-cell-type comparison)
|   Most common BixBench pattern (bix-33)
|   See: analysis_patterns.md "Pattern 1"
|
+-- CORRELATION ANALYSIS (gene property vs expression)
|   Pattern: Gene length vs expression (bix-22)
|   See: analysis_patterns.md "Pattern 2"
|
+-- CLUSTERING & PCA (expression matrix analysis)
|   See: references/clustering_guide.md
|
+-- CELL COMMUNICATION (ligand-receptor interactions)
|   See: references/cell_communication.md
|
+-- TRAJECTORY ANALYSIS (pseudotime)
    See: references/trajectory_analysis.md
```

**Data format handling**:
- h5ad -> `sc.read_h5ad()`
- 10X -> `sc.read_10x_mtx()` or `sc.read_10x_h5()`
- CSV/TSV -> `pd.read_csv()` -> Convert to AnnData (check orientation!)

---

## Data Loading

AnnData expects: **cells/samples as rows (obs), genes as columns (var)**

```python
adata = sc.read_h5ad("data.h5ad")  # h5ad already oriented

# CSV/TSV: check orientation
df = pd.read_csv("counts.csv", index_col=0)
if df.shape[0] > df.shape[1] * 5:  # genes > samples by 5x => transpose
    df = df.T
adata = ad.AnnData(df)

# Load metadata
meta = pd.read_csv("metadata.csv", index_col=0)
common = adata.obs_names.intersection(meta.index)
adata = adata[common].copy()
for col in meta.columns:
    adata.obs[col] = meta.loc[common, col]
```

---

## Quality Control

```python
adata.var['mt'] = adata.var_names.str.startswith(('MT-', 'mt-'))
sc.pp.calculate_qc_metrics(adata, qc_vars=['mt'], inplace=True)
sc.pp.filter_cells(adata, min_genes=200)
adata = adata[adata.obs['pct_counts_mt'] < 20].copy()
sc.pp.filter_genes(adata, min_cells=3)
```

See: references/scanpy_workflow.md for details

---

## Complete Pipeline (Quick Reference)

```python
import scanpy as sc

adata = sc.read_10x_h5("filtered_feature_bc_matrix.h5")

# QC
adata.var['mt'] = adata.var_names.str.startswith('MT-')
sc.pp.calculate_qc_metrics(adata, qc_vars=['mt'], inplace=True)
adata = adata[adata.obs['pct_counts_mt'] < 20].copy()
sc.pp.filter_cells(adata, min_genes=200)
sc.pp.filter_genes(adata, min_cells=3)

# Normalize + HVG + PCA
sc.pp.normalize_total(adata, target_sum=1e4)
sc.pp.log1p(adata)
adata.raw = adata.copy()
sc.pp.highly_variable_genes(adata, n_top_genes=2000)
sc.tl.pca(adata, n_comps=50)

# Cluster + UMAP
sc.pp.neighbors(adata, n_pcs=30)
sc.tl.leiden(adata, resolution=0.5)
sc.tl.umap(adata)

# Find markers + Annotate + Per-cell-type DE
sc.tl.rank_genes_groups(adata, groupby='leiden', method='wilcoxon')
```

---

## Differential Expression Decision Tree

```
Single-Cell DE (many cells per condition):
  Use: sc.tl.rank_genes_groups(), methods: wilcoxon, t-test, logreg
  Best for: Per-cell-type DE, marker gene finding

Pseudo-Bulk DE (aggregate counts by sample):
  Use: DESeq2 via PyDESeq2
  Best for: Sample-level comparisons with replicates

Statistical Tests Only:
  Use: scipy.stats (ttest_ind, f_oneway, pearsonr)
  Best for: Correlation, ANOVA, t-tests on summaries
```

---

## Statistical Tests (Quick Reference)

```python
from scipy import stats
from statsmodels.stats.multitest import multipletests

# Pearson/Spearman correlation
r, p = stats.pearsonr(gene_lengths, mean_expression)

# Welch's t-test
t_stat, p_val = stats.ttest_ind(group1, group2, equal_var=False)

# ANOVA
f_stat, p_val = stats.f_oneway(group1, group2, group3)

# Multiple testing correction (BH)
reject, pvals_adj, _, _ = multipletests(pvals, method='fdr_bh')
```

---

## Batch Correction (Harmony)

```python
import harmonypy
sc.tl.pca(adata, n_comps=50)
ho = harmonypy.run_harmony(adata.obsm['X_pca'][:, :30], adata.obs, 'batch', random_state=0)
adata.obsm['X_pca_harmony'] = ho.Z_corr.T
sc.pp.neighbors(adata, use_rep='X_pca_harmony')
sc.tl.leiden(adata, resolution=0.5)
sc.tl.umap(adata)
```

---

## ToolUniverse Integration

### Data Discovery (before analysis)
- **CxGDisc_search_datasets**: Search CELLxGENE Discover for scRNA-seq datasets by disease, tissue, organism. Use broad disease terms (e.g., "breast cancer" not "triple-negative").
- **GEO_search_rnaseq_datasets** / **geo_search_datasets**: Search GEO for scRNA-seq studies
- **NCBI_SRA_search_runs**: Search SRA for sequencing runs (query="single cell RNA-seq [disease]")
- **OmicsDI_search_datasets**: Cross-repository dataset search

### Cell Type Markers
- **CellMarker_search_by_cell_type**: Tissue-specific cell markers (use `CellMarker_list_cell_types` first — exact names required, e.g., "Regulatory T(Treg) cell" not "Regulatory T cell")
- **CellMarker_search_cancer_markers**: Cancer-context markers with experimental evidence
- **CellMarker_search_by_gene**: Reverse lookup — which cell types express a gene?
- **HPA_search_genes_by_query**: Cell-type marker gene search

### Gene Annotation
- **MyGene_query_genes** / **MyGene_batch_query**: Gene ID conversion
- **ensembl_lookup_gene**: Ensembl gene details
- **UniProt_get_function_by_accession**: Protein function

### Cell-Cell Communication
- **OmniPath_get_ligand_receptor_interactions**: L-R pairs (CellPhoneDB, CellChatDB)
- **OmniPath_get_signaling_interactions**: Downstream signaling
- **OmniPath_get_complexes**: Multi-subunit receptors

### Enrichment (Post-DE)
- **PANTHER_enrichment**: GO enrichment (BP, MF, CC)
- **STRING_functional_enrichment**: Network-based enrichment
- **ReactomeAnalysis_pathway_enrichment**: Reactome pathways

### Clinical Context (for tumor immunology)
- **DGIdb_get_drug_gene_interactions**: Drug interactions for immune checkpoint targets (genes=["CD274"] for PD-L1)
- **civic_search_evidence_items**: Clinical evidence for mutations/biomarkers
- **TIMER2_immune_estimation**: TCGA immune infiltration correlation
- **search_clinical_trials**: Clinical trial matching
- **GTEx_get_expression_summary**: Normal tissue baseline expression
- **PubMed_search_articles**: Literature context

---

## Scanpy vs Seurat Equivalents

| Operation | Seurat (R) | Scanpy (Python) |
|-----------|------------|-----------------|
| Load data | `Read10X()` | `sc.read_10x_mtx()` |
| Normalize | `NormalizeData()` | `sc.pp.normalize_total() + sc.pp.log1p()` |
| Find HVGs | `FindVariableFeatures()` | `sc.pp.highly_variable_genes()` |
| PCA | `RunPCA()` | `sc.tl.pca()` |
| Cluster | `FindClusters()` | `sc.tl.leiden()` |
| UMAP | `RunUMAP()` | `sc.tl.umap()` |
| Find markers | `FindMarkers()` | `sc.tl.rank_genes_groups()` |
| Batch correction | `RunHarmony()` | `harmonypy.run_harmony()` |

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: leidenalg` | `pip install leidenalg` |
| Sparse matrix errors | `.toarray()`: `X = adata.X.toarray() if issparse(adata.X) else adata.X` |
| Wrong matrix orientation | More genes than samples? Transpose |
| NaN in correlation | Filter: `valid = ~np.isnan(x) & ~np.isnan(y)` |
| Too few cells for DE | Need >= 3 cells per condition per cell type |
| Memory error | Use `sc.pp.highly_variable_genes()` to reduce features |

---

## Reference Documentation

**Detailed Analysis Patterns**: analysis_patterns.md (per-cell-type DE, correlation, PCA, ANOVA, cell communication)

**Core Workflows**:
- references/scanpy_workflow.md - Complete scanpy pipeline
- references/seurat_workflow.md - Seurat to Scanpy translation
- references/clustering_guide.md - Clustering methods
- references/marker_identification.md - Marker genes, annotation
- references/trajectory_analysis.md - Pseudotime
- references/cell_communication.md - OmniPath/CellPhoneDB workflow
- references/troubleshooting.md - Detailed error solutions
