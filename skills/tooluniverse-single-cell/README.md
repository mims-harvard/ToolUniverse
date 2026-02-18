# tooluniverse-single-cell

Production-ready single-cell genomics and expression matrix analysis skill for BixBench.

## Overview

This skill provides comprehensive single-cell RNA-seq analysis using scanpy, anndata, scipy, and ToolUniverse. It handles both full scRNA-seq workflows (raw counts to annotated cell types) and targeted expression-level analyses (per-cell-type differential expression, gene correlation, clustering, ANOVA).

## BixBench Coverage

**18+ questions across 5 projects:**

| Project | Questions | Analysis Type |
|---------|-----------|---------------|
| bix-22 | 5 | Gene length vs expression correlation by immune cell type |
| bix-27 | 3 | PCA on expression matrix, hierarchical/bootstrap clustering |
| bix-31 | 4 | Cell-type-specific DE, t-tests comparing cell types |
| bix-33 | 2 | Single-cell DE by cell type after treatment |
| bix-36 | 4 | miRNA expression ANOVA across cell types, fold changes |

## Capabilities

| Capability | Implementation |
|-----------|---------------|
| Data loading | h5ad, 10X, CSV/TSV count matrices via scanpy/anndata |
| Quality control | Cell/gene filtering, QC metrics, doublet detection |
| Normalization | Library-size normalization, log1p, z-score scaling |
| Dimensionality reduction | PCA (scanpy + sklearn), UMAP, t-SNE |
| Clustering | Leiden, Louvain, hierarchical, bootstrap consensus |
| Batch correction | Harmony, ComBat |
| Differential expression | Wilcoxon, t-test (scanpy), DESeq2 (pseudo-bulk) |
| Per-cell-type DE | Automated per-cell-type condition comparison |
| Statistical analysis | Pearson/Spearman correlation, t-test, Welch's, ANOVA |
| **Cell-cell communication** | **OmniPath L-R interactions, CellPhoneDB, CellChatDB** |
| Fold changes | Log2FC computation, median FC, distribution analysis |
| Multiple testing | BH, Bonferroni, BY correction |
| Cell type annotation | Marker gene scoring, ToolUniverse databases (HPA, MyGene) |
| Enrichment | gseapy ORA (GO, KEGG, Reactome, 220+ libraries) |
| Gene annotation | HPA, Ensembl, MyGene, UniProt via ToolUniverse |

## Required Packages

```bash
pip install scanpy anndata leidenalg umap-learn harmonypy gseapy pandas numpy scipy scikit-learn statsmodels
```

Optional:
```bash
pip install pydeseq2  # for pseudo-bulk DESeq2
```

## Test Results

```
Total tests: 72
Passed: 72
Failed: 0
Success rate: 100.0%
```

### Test Coverage

| Test Group | Tests | Status |
|-----------|-------|--------|
| Data Loading | 5 | All pass |
| QC and Preprocessing | 7 | All pass |
| PCA | 4 | All pass |
| Clustering | 4 | All pass |
| Differential Expression | 7 | All pass |
| Correlation Analysis | 5 | All pass |
| Statistical Comparisons | 9 | All pass |
| Fold Change and DE Comparison | 4 | All pass |
| miRNA Analysis | 4 | All pass |
| Batch Correction | 3 | All pass |
| Cell Type Annotation | 2 | All pass |
| Enrichment Integration | 2 | All pass |
| ToolUniverse Integration | 3 | All pass |
| Edge Cases | 7 | All pass |
| Report Generation | 2 | All pass |
| Complete Pipeline | 4 | All pass |

## File Structure

```
tooluniverse-single-cell/
├── SKILL.md              - Main skill documentation (719 lines, redesigned 2026-02-17)
├── SKILL_OLD.md          - Original skill doc (2122 lines, backup)
├── QUICK_START.md        - Quick start guide with 8 examples
├── README.md             - This file
├── test_skill.py         - Test suite (72 tests, 100% pass rate)
├── REDESIGN_SUMMARY.md   - Redesign documentation
│
├── references/           - Detailed workflow guides (7 files)
│   ├── scanpy_workflow.md       - Complete scanpy pipeline (QC, normalize, cluster, DE)
│   ├── cell_communication.md    - OmniPath/CellPhoneDB integration (L-R interactions)
│   ├── clustering_guide.md      - Leiden, Louvain, hierarchical, bootstrap consensus
│   ├── marker_identification.md - Marker genes, cell type annotation
│   ├── trajectory_analysis.md   - Pseudotime, PAGA, trajectory inference
│   ├── seurat_workflow.md       - Seurat → Scanpy translation
│   └── troubleshooting.md       - Common errors and solutions
│
└── scripts/              - Utility scripts (3 files)
    ├── qc_metrics.py      - Calculate QC, apply filters
    ├── normalize_data.py  - Normalization pipeline
    └── find_markers.py    - Find markers, annotate cell types
```

### Documentation Organization

- **SKILL.md**: High-level workflows, decision trees, BixBench patterns (start here)
- **references/**: Detailed implementation guides (dive deep when needed)
- **scripts/**: Ready-to-use utilities (for common operations)

## Quick Start

### New User? Start Here
1. Read `SKILL.md` - High-level overview and decision trees
2. Try examples in `QUICK_START.md` - 8 worked examples
3. Explore `references/` - Detailed workflows when needed

### Basic Workflow

```python
import scanpy as sc

# Load data
adata = sc.read_h5ad("data.h5ad")

# Standard pipeline
sc.pp.normalize_total(adata, target_sum=1e4)
sc.pp.log1p(adata)
sc.pp.highly_variable_genes(adata, n_top_genes=2000)
sc.tl.pca(adata, n_comps=50)
sc.pp.neighbors(adata, n_pcs=30)
sc.tl.leiden(adata, resolution=0.5)

# Per-cell-type DE
for ct in adata.obs['cell_type'].unique():
    adata_ct = adata[adata.obs['cell_type'] == ct].copy()
    sc.tl.rank_genes_groups(adata_ct, groupby='condition',
                             groups=['treatment'], reference='control',
                             method='wilcoxon')
    df = sc.get.rank_genes_groups_df(adata_ct, group='treatment')
    n_sig = (df['pvals_adj'] < 0.05).sum()
    print(f"{ct}: {n_sig} DEGs")
```

## Related Skills

- `tooluniverse-rnaseq-deseq2`: Bulk RNA-seq DESeq2 analysis
- `tooluniverse-gene-enrichment`: Gene enrichment and pathway analysis
- `tooluniverse-statistical-modeling`: Statistical regression and survival analysis
- `tooluniverse-variant-analysis`: VCF processing and variant annotation
