---
name: tooluniverse-single-cell
description: Production-ready single-cell and expression matrix analysis using scanpy, anndata, and scipy. Performs scRNA-seq QC, normalization, PCA, UMAP, Leiden/Louvain clustering, differential expression (Wilcoxon, t-test, DESeq2), cell type annotation, per-cell-type statistical analysis, gene-expression correlation, batch correction (Harmony), trajectory inference, and cell-cell communication analysis. NEW: Analyzes ligand-receptor interactions between cell types using OmniPath (CellPhoneDB, CellChatDB), scores communication strength, identifies signaling cascades, and handles multi-subunit receptor complexes. Integrates with ToolUniverse gene annotation tools (HPA, Ensembl, MyGene, UniProt) and enrichment tools (gseapy, PANTHER, STRING). Supports h5ad, 10X, CSV/TSV count matrices, and pre-annotated datasets. Use when analyzing single-cell RNA-seq data, studying cell-cell interactions, performing cell type differential expression, computing gene-expression correlations by cell type, analyzing tumor-immune communication, or answering questions about scRNA-seq datasets.
---

# Single-Cell Genomics and Expression Matrix Analysis

Comprehensive single-cell RNA-seq analysis and expression matrix processing using scanpy, anndata, scipy, and ToolUniverse. Designed for both full scRNA-seq workflows (raw counts to annotated cell types) and targeted expression-level analyses (per-cell-type DE, correlation, ANOVA, clustering).

**KEY PRINCIPLES**:
1. **Data-first approach** - Load, inspect, and validate data before any analysis
2. **AnnData-centric** - All data flows through anndata objects for consistency
3. **Cell type awareness** - Many questions require per-cell-type subsetting and analysis
4. **Statistical rigor** - Proper normalization, multiple testing correction, effect sizes
5. **Scanpy standard pipeline** - Follow established best practices for scRNA-seq
6. **Flexible input** - Handle h5ad, 10X, CSV/TSV, pre-processed and raw data
7. **Question-driven** - Parse what the user is actually asking and extract the specific answer
8. **Enrichment integration** - Chain DE results into GO/KEGG/Reactome enrichment when requested
9. **Large dataset support** - Efficient handling of datasets with >100k cells

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
- Ask about marker genes for cell populations
- Need batch correction (Harmony, combat)
- Want trajectory or pseudotime analysis
- Questions mention "single-cell", "scRNA-seq", "cell type", "h5ad"
- Questions involve immune cell types (CD4, CD8, CD14, CD19, monocytes, etc.)
- Need hierarchical clustering of expression data with bootstrap consensus

**BixBench Coverage**: 18+ questions across 5 projects (bix-22, bix-27, bix-31, bix-33, bix-36)

**NOT for** (use other skills instead):
- Bulk RNA-seq DESeq2 analysis only -> Use `tooluniverse-rnaseq-deseq2`
- Gene enrichment only (no expression data) -> Use `tooluniverse-gene-enrichment`
- VCF/variant analysis -> Use `tooluniverse-variant-analysis`
- Statistical modeling (regression, survival) -> Use `tooluniverse-statistical-modeling`

---

## Required Python Packages

```python
# Core (MUST be installed)
import scanpy as sc
import anndata as ad
import pandas as pd
import numpy as np
from scipy import stats
from scipy.cluster.hierarchy import linkage, fcluster, dendrogram
from scipy.spatial.distance import pdist
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from statsmodels.stats.multitest import multipletests

# Enrichment (for GO/KEGG/Reactome follow-up)
import gseapy as gp

# Optional
import harmonypy  # batch correction
```

**Installation** (if not already present):
```bash
pip install scanpy anndata leidenalg umap-learn harmonypy gseapy pandas numpy scipy scikit-learn statsmodels
```

---

## Phase 0: Question Parsing and Input Identification

**CRITICAL FIRST STEP**: Before writing ANY code, parse the question to identify:

### 0.1 What Data Files Are Available?

Look in the working directory or data folder for:
- **h5ad files**: `*.h5ad` - AnnData format, may contain everything (counts, metadata, embeddings, cell types)
- **10X files**: `matrix.mtx`, `barcodes.tsv`, `genes.tsv` (or `features.tsv`)
- **Count matrices**: `*.csv`, `*.tsv`, `*counts*`, `*expression*`
- **Metadata/annotations**: `*metadata*`, `*obs*`, `*cell_type*`, `*annotation*`
- **Gene annotations**: `*gene_info*`, `*gencode*`, `*gtf*`, `*gene_length*`

```python
import os, glob

data_dir = "."  # or specified path
all_files = glob.glob(os.path.join(data_dir, "**/*"), recursive=True)
data_files = [f for f in all_files if f.endswith(('.h5ad', '.csv', '.tsv', '.txt', '.h5', '.mtx', '.gz'))]
print("Available data files:", data_files)
```

### 0.2 Parse the Question Requirements

Extract these parameters from the question:

| Parameter | Default | Example Question Text |
|-----------|---------|----------------------|
| **Cell type column** | Auto-detect | "immune cell type", "cell_type", "cluster" |
| **Cell types to analyze** | All | "CD4/CD8 cells", "CD14 Monocytes", "excluding PBMCs" |
| **Condition column** | Auto-detect | "treatment vs control", "M vs F", "AAV9 vs untreated" |
| **Gene filter** | None | "protein-coding genes", "miRNAs" |
| **Statistic requested** | Varies | "Pearson correlation", "t-statistic", "F-statistic", "p-value" |
| **padj threshold** | 0.05 | "adjusted p-value < 0.05" |
| **log2FC threshold** | 0 | "|log2FC| > 0.5" |
| **baseMean threshold** | 0 | "baseMean > 10" |
| **LFC shrinkage** | No | "using lfc shrinkage" |
| **Normalization** | Auto | "log2 transformation", "log1p", "TPM" |
| **Clustering method** | Leiden | "Louvain clustering", "hierarchical clustering" |
| **Correlation type** | Pearson | "Spearman correlation" |
| **Multiple testing** | BH | "Bonferroni", "Benjamini-Yekutieli" |

### 0.3 Decision Tree

```
Q: Is there an h5ad file?
  YES -> Load with anndata. Check if it contains:
         - Raw counts (adata.X or adata.layers['counts'])
         - Pre-computed clusters (adata.obs)
         - Pre-computed embeddings (adata.obsm)
         -> Decide: Full pipeline or targeted analysis?
  NO  -> Q: Are there 10X files (matrix.mtx, barcodes.tsv, genes.tsv)?
           YES -> Load with sc.read_10x_mtx()
           NO  -> Q: Is there a CSV/TSV expression matrix?
                    YES -> Load as DataFrame, convert to AnnData
                    NO  -> ERROR: No suitable input data found

Q: Does the question ask about specific cell types?
  YES -> Subset data by cell type before analysis
  NO  -> Analyze all cells/samples

Q: Does the question ask for DE analysis?
  YES -> Q: Is this single-cell DE (many cells per condition)?
           YES -> Use scanpy.tl.rank_genes_groups (Wilcoxon/t-test)
           NO  -> Use DESeq2 via tooluniverse-rnaseq-deseq2 skill
  NO  -> Continue to other analysis types

Q: Does the question ask for correlation/statistical test?
  YES -> Use scipy.stats (pearsonr, spearmanr, ttest_ind, f_oneway)
  NO  -> Continue to clustering/visualization
```

---

## Phase 1: Data Loading and Validation

### 1.1 Load Data from Various Formats

```python
import scanpy as sc
import anndata as ad
import pandas as pd
import numpy as np
import os

def load_single_cell_data(file_path, **kwargs):
    """Load single-cell or expression data from various formats.

    Returns:
        adata: AnnData object
    """
    if isinstance(file_path, str):
        ext = os.path.splitext(file_path)[1].lower()
    else:
        ext = None

    if ext == '.h5ad':
        adata = sc.read_h5ad(file_path)
    elif ext == '.h5':
        adata = sc.read_10x_h5(file_path)
    elif ext in ['.csv']:
        df = pd.read_csv(file_path, index_col=0, **kwargs)
        adata = ad.AnnData(df)
    elif ext in ['.tsv', '.txt']:
        df = pd.read_csv(file_path, sep='\t', index_col=0, **kwargs)
        adata = ad.AnnData(df)
    elif ext == '.mtx' or (isinstance(file_path, str) and os.path.isdir(file_path)):
        # 10X directory format
        adata = sc.read_10x_mtx(file_path if os.path.isdir(file_path)
                                 else os.path.dirname(file_path))
    else:
        # Try tab-separated as default
        df = pd.read_csv(file_path, sep='\t', index_col=0, **kwargs)
        adata = ad.AnnData(df)

    return adata
```

### 1.2 Orient Expression Matrix

**CRITICAL**: Expression data can be genes-by-samples or samples-by-genes.
- AnnData convention: observations (cells/samples) as rows, variables (genes) as columns
- If loaded from CSV with genes as rows: transpose

```python
def orient_expression_matrix(df, metadata_samples=None):
    """Ensure cells/samples are rows and genes are columns.

    AnnData expects: cells/samples as rows (obs), genes as columns (var).
    """
    if metadata_samples is not None:
        row_match = len(set(df.index) & set(metadata_samples))
        col_match = len(set(df.columns) & set(metadata_samples))
        if col_match > row_match:
            df = df.T
        return df

    # Heuristic: typically more genes than samples
    if df.shape[0] > df.shape[1] * 5:
        df = df.T  # Genes were rows, transpose

    return df
```

### 1.3 Load and Attach Metadata

```python
def load_metadata(adata, metadata_path, sep=None):
    """Load cell/sample metadata and attach to AnnData.obs."""
    if sep is None:
        if metadata_path.endswith('.csv'):
            sep = ','
        else:
            sep = '\t'

    meta = pd.read_csv(metadata_path, index_col=0, sep=sep)

    # Align indices
    common = adata.obs_names.intersection(meta.index)
    if len(common) == 0:
        # Try matching against columns
        common_cols = adata.obs_names.intersection(meta.columns)
        if len(common_cols) > 0:
            meta = meta.T
            common = adata.obs_names.intersection(meta.index)

    if len(common) > 0:
        adata = adata[common].copy()
        for col in meta.columns:
            adata.obs[col] = meta.loc[common, col].values

    return adata
```

### 1.4 Load Gene Annotations

Many BixBench questions require gene metadata (gene length, biotype, chromosome).

```python
def load_gene_annotations(adata, gene_info_path=None, sep=None):
    """Load gene annotations and attach to AnnData.var.

    Commonly needed: gene_length, gene_type/biotype (protein_coding, lncRNA, miRNA).
    """
    if gene_info_path is None:
        return adata

    if sep is None:
        if gene_info_path.endswith('.csv'):
            sep = ','
        else:
            sep = '\t'

    gene_info = pd.read_csv(gene_info_path, index_col=0, sep=sep)

    # Match gene names
    common_genes = adata.var_names.intersection(gene_info.index)
    if len(common_genes) == 0:
        # Try matching by column (e.g., gene_name, symbol)
        for col in ['gene_name', 'symbol', 'gene_symbol', 'Symbol', 'Gene']:
            if col in gene_info.columns:
                gene_info_reindexed = gene_info.set_index(col)
                common_genes = adata.var_names.intersection(gene_info_reindexed.index)
                if len(common_genes) > 0:
                    gene_info = gene_info_reindexed
                    break

    if len(common_genes) > 0:
        for col in gene_info.columns:
            adata.var[col] = gene_info.loc[adata.var_names.intersection(gene_info.index), col].reindex(adata.var_names)

    return adata
```

### 1.5 Validate and Filter

```python
def validate_adata(adata):
    """Validate AnnData object and apply basic filters."""
    issues = []

    # Check for sparse matrix
    from scipy.sparse import issparse
    if issparse(adata.X):
        issues.append(f"Sparse matrix: {type(adata.X).__name__}")

    # Basic stats
    issues.append(f"Shape: {adata.n_obs} cells/samples x {adata.n_vars} genes")
    issues.append(f"Obs columns: {list(adata.obs.columns)}")
    issues.append(f"Var columns: {list(adata.var.columns)}")

    # Check for NaN/Inf
    X = adata.X.toarray() if issparse(adata.X) else adata.X
    if np.any(np.isnan(X)):
        issues.append("WARNING: NaN values detected in expression matrix")
    if np.any(np.isinf(X)):
        issues.append("WARNING: Inf values detected in expression matrix")

    return issues
```

---

## Phase 2: Quality Control and Preprocessing

### 2.1 Standard scRNA-seq QC

```python
def run_qc(adata, min_genes=200, min_cells=3, max_pct_mito=20,
           max_genes=None, min_counts=None, max_counts=None):
    """Run standard scRNA-seq quality control.

    Args:
        adata: AnnData object with raw counts
        min_genes: Minimum genes per cell
        min_cells: Minimum cells per gene
        max_pct_mito: Maximum percentage mitochondrial genes
        max_genes: Maximum genes per cell (doublet filter)
        min_counts: Minimum total counts per cell
        max_counts: Maximum total counts per cell

    Returns:
        adata: Filtered AnnData object
    """
    # Calculate QC metrics
    adata.var['mt'] = adata.var_names.str.startswith(('MT-', 'mt-'))
    sc.pp.calculate_qc_metrics(adata, qc_vars=['mt'],
                                percent_top=None, log1p=False, inplace=True)

    n_before = adata.n_obs

    # Filter cells
    sc.pp.filter_cells(adata, min_genes=min_genes)
    if min_counts is not None:
        sc.pp.filter_cells(adata, min_counts=min_counts)
    if max_counts is not None:
        adata = adata[adata.obs['total_counts'] < max_counts].copy()
    if max_genes is not None:
        adata = adata[adata.obs['n_genes_by_counts'] < max_genes].copy()

    # Filter by mito content
    if 'pct_counts_mt' in adata.obs.columns:
        adata = adata[adata.obs['pct_counts_mt'] < max_pct_mito].copy()

    # Filter genes
    sc.pp.filter_genes(adata, min_cells=min_cells)

    n_after = adata.n_obs
    print(f"QC: {n_before} -> {n_after} cells ({n_before - n_after} removed)")

    return adata
```

### 2.2 Doublet Detection

```python
def detect_doublets(adata, threshold=0.25):
    """Detect doublets using scrublet-like approach via scanpy.

    Args:
        adata: AnnData with raw counts
        threshold: Doublet score threshold

    Returns:
        adata: With 'predicted_doublet' and 'doublet_score' in obs
    """
    try:
        sc.external.pp.scrublet(adata, expected_doublet_rate=0.06)
        n_doublets = adata.obs['predicted_doublet'].sum()
        print(f"Detected {n_doublets} doublets ({n_doublets/adata.n_obs*100:.1f}%)")
    except Exception as e:
        print(f"Doublet detection failed: {e}. Continuing without removal.")

    return adata
```

### 2.3 Normalization and Scaling

```python
def normalize_and_scale(adata, target_sum=1e4, log_transform=True,
                        n_top_genes=2000, scale=True, max_value=10):
    """Standard normalization pipeline.

    Args:
        adata: AnnData with raw counts
        target_sum: Target sum for library-size normalization
        log_transform: Whether to log1p transform
        n_top_genes: Number of highly variable genes to select (0 = skip)
        scale: Whether to z-score scale
        max_value: Maximum value after scaling

    Returns:
        adata: Normalized AnnData (raw counts in adata.raw)
    """
    # Store raw counts
    adata.raw = adata.copy()

    # Library-size normalization
    sc.pp.normalize_total(adata, target_sum=target_sum)

    # Log transform
    if log_transform:
        sc.pp.log1p(adata)

    # Highly variable genes
    if n_top_genes > 0:
        sc.pp.highly_variable_genes(adata, n_top_genes=min(n_top_genes, adata.n_vars),
                                     flavor='seurat_v3' if not log_transform else 'seurat')

    # Scale
    if scale:
        sc.pp.scale(adata, max_value=max_value)

    return adata
```

---

## Phase 3: Dimensionality Reduction and Clustering

### 3.1 PCA

```python
def run_pca(adata, n_comps=50, use_highly_variable=True):
    """Run PCA on expression data.

    For BixBench questions about PCA:
    - Variance explained: adata.uns['pca']['variance_ratio']
    - PC loadings: adata.varm['PCs']
    - PC coordinates: adata.obsm['X_pca']
    """
    if use_highly_variable and 'highly_variable' in adata.var.columns:
        n_comps = min(n_comps, sum(adata.var['highly_variable']), adata.n_obs - 1)
    else:
        n_comps = min(n_comps, adata.n_vars, adata.n_obs - 1)

    sc.tl.pca(adata, n_comps=n_comps, use_highly_variable=use_highly_variable)

    # Report variance explained
    var_ratio = adata.uns['pca']['variance_ratio']
    print(f"PC1 explains {var_ratio[0]*100:.2f}% of variance")
    print(f"Top 10 PCs explain {sum(var_ratio[:10])*100:.2f}% of variance")

    return adata
```

### 3.1b Manual PCA (for BixBench questions requiring specific transforms)

Some BixBench questions specify exact PCA parameters (e.g., log10 with pseudocount).

```python
def manual_pca(expression_df, log_transform='log10', pseudocount=1):
    """Run PCA manually on a DataFrame for precise control.

    Args:
        expression_df: DataFrame with samples as rows, genes as columns
        log_transform: 'log10', 'log2', 'log1p', or None
        pseudocount: Pseudocount for log transform

    Returns:
        dict with pca_result, variance_explained, pc_coords
    """
    from sklearn.decomposition import PCA as skPCA

    X = expression_df.values.astype(float)

    # Apply transform
    if log_transform == 'log10':
        X = np.log10(X + pseudocount)
    elif log_transform == 'log2':
        X = np.log2(X + pseudocount)
    elif log_transform == 'log1p':
        X = np.log1p(X)

    # Fit PCA
    n_components = min(X.shape[0], X.shape[1])
    pca = skPCA(n_components=n_components)
    pc_coords = pca.fit_transform(X)

    result = {
        'variance_ratio': pca.explained_variance_ratio_,
        'variance_explained': pca.explained_variance_,
        'pc_coords': pd.DataFrame(pc_coords, index=expression_df.index,
                                   columns=[f'PC{i+1}' for i in range(n_components)]),
        'loadings': pd.DataFrame(pca.components_.T, index=expression_df.columns,
                                  columns=[f'PC{i+1}' for i in range(n_components)]),
        'cumulative_variance': np.cumsum(pca.explained_variance_ratio_),
    }

    print(f"PC1: {result['variance_ratio'][0]*100:.2f}% variance")
    return result
```

### 3.2 Neighbor Graph and Clustering

```python
def cluster_cells(adata, n_neighbors=15, n_pcs=None, resolution=1.0,
                  method='leiden', random_state=0):
    """Build neighbor graph and cluster cells.

    Args:
        adata: AnnData with PCA computed
        n_neighbors: Number of neighbors for graph
        n_pcs: Number of PCs to use (None = auto)
        resolution: Clustering resolution (higher = more clusters)
        method: 'leiden' or 'louvain'
        random_state: Random seed for reproducibility

    Returns:
        adata: With clustering in adata.obs['leiden'] or adata.obs['louvain']
    """
    if n_pcs is None:
        n_pcs = min(30, adata.obsm['X_pca'].shape[1])

    sc.pp.neighbors(adata, n_neighbors=n_neighbors, n_pcs=n_pcs, random_state=random_state)

    if method == 'leiden':
        sc.tl.leiden(adata, resolution=resolution, random_state=random_state)
        cluster_col = 'leiden'
    elif method == 'louvain':
        sc.tl.louvain(adata, resolution=resolution, random_state=random_state)
        cluster_col = 'louvain'

    n_clusters = adata.obs[cluster_col].nunique()
    print(f"{method.capitalize()} clustering: {n_clusters} clusters (resolution={resolution})")

    return adata
```

### 3.3 UMAP / t-SNE

```python
def compute_embeddings(adata, method='umap', random_state=0, **kwargs):
    """Compute 2D embeddings for visualization.

    Args:
        adata: AnnData with neighbor graph
        method: 'umap' or 'tsne'
    """
    if method == 'umap':
        sc.tl.umap(adata, random_state=random_state, **kwargs)
    elif method == 'tsne':
        sc.tl.tsne(adata, random_state=random_state, **kwargs)

    return adata
```

### 3.4 Hierarchical Clustering (for expression matrices)

```python
def hierarchical_clustering(expression_df, n_clusters=3, method='ward',
                            metric='euclidean'):
    """Perform hierarchical clustering on expression data.

    Args:
        expression_df: DataFrame (samples as rows, genes as columns)
        n_clusters: Number of clusters to cut dendrogram into
        method: Linkage method ('ward', 'complete', 'average', 'single')
        metric: Distance metric

    Returns:
        dict with cluster_labels, linkage_matrix, dendrogram_data
    """
    from scipy.cluster.hierarchy import linkage, fcluster
    from scipy.spatial.distance import pdist

    # Compute distances
    if method == 'ward':
        Z = linkage(expression_df.values, method='ward')
    else:
        dist = pdist(expression_df.values, metric=metric)
        Z = linkage(dist, method=method)

    # Cut into clusters
    labels = fcluster(Z, t=n_clusters, criterion='maxclust')

    result = {
        'labels': pd.Series(labels, index=expression_df.index, name='cluster'),
        'linkage_matrix': Z,
        'n_clusters': n_clusters,
    }

    # Cluster sizes
    for c in range(1, n_clusters + 1):
        n = (labels == c).sum()
        print(f"  Cluster {c}: {n} samples")

    return result
```

### 3.5 Bootstrap Consensus Clustering

For BixBench questions asking about consensus clustering with bootstrap.

```python
def bootstrap_consensus_clustering(expression_df, n_clusters=3, n_iterations=50,
                                    train_fraction=0.7, random_state=42):
    """Bootstrap consensus clustering with logistic regression prediction.

    Args:
        expression_df: DataFrame (samples as rows, genes as columns)
        n_clusters: Number of clusters
        n_iterations: Number of bootstrap iterations
        train_fraction: Fraction of data for training
        random_state: Random seed

    Returns:
        dict with consensus_labels, consistency_count, consensus_matrix
    """
    from scipy.cluster.hierarchy import linkage, fcluster
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    np.random.seed(random_state)
    n_samples = len(expression_df)
    n_train = int(n_samples * train_fraction)

    # Consensus matrices (co-clustering frequency)
    train_consensus = np.zeros((n_samples, n_samples))
    test_consensus = np.zeros((n_samples, n_samples))
    train_count = np.zeros((n_samples, n_samples))
    test_count = np.zeros((n_samples, n_samples))

    for i in range(n_iterations):
        # Random split
        indices = np.random.permutation(n_samples)
        train_idx = indices[:n_train]
        test_idx = indices[n_train:]

        # Cluster training data
        train_data = expression_df.iloc[train_idx]
        Z = linkage(train_data.values, method='ward')
        train_labels = fcluster(Z, t=n_clusters, criterion='maxclust')

        # Update train consensus
        for a_i, a in enumerate(train_idx):
            for b_i, b in enumerate(train_idx):
                train_count[a, b] += 1
                if train_labels[a_i] == train_labels[b_i]:
                    train_consensus[a, b] += 1

        # Predict test labels using logistic regression
        scaler = StandardScaler()
        X_train = scaler.fit_transform(train_data.values)
        X_test = scaler.transform(expression_df.iloc[test_idx].values)

        lr = LogisticRegression(max_iter=1000, random_state=random_state)
        lr.fit(X_train, train_labels)
        test_labels = lr.predict(X_test)

        # Update test consensus
        for a_i, a in enumerate(test_idx):
            for b_i, b in enumerate(test_idx):
                test_count[a, b] += 1
                if test_labels[a_i] == test_labels[b_i]:
                    test_consensus[a, b] += 1

    # Normalize consensus matrices
    with np.errstate(divide='ignore', invalid='ignore'):
        train_consensus_norm = np.where(train_count > 0, train_consensus / train_count, 0)
        test_consensus_norm = np.where(test_count > 0, test_consensus / test_count, 0)

    # Final clustering from combined consensus
    combined_consensus = (train_consensus_norm + test_consensus_norm) / 2
    np.fill_diagonal(combined_consensus, 1.0)

    # Cluster the consensus matrix
    from scipy.spatial.distance import squareform
    dist = 1 - combined_consensus
    np.fill_diagonal(dist, 0)
    dist = np.maximum(dist, 0)  # ensure non-negative
    dist = (dist + dist.T) / 2  # ensure symmetry
    condensed = squareform(dist)
    Z_final = linkage(condensed, method='average')
    final_labels = fcluster(Z_final, t=n_clusters, criterion='maxclust')

    # Count consistently classified samples
    # A sample is "consistently classified" if its consensus score with
    # its cluster members is high (> 0.7) in BOTH train and test
    consistent_count = 0
    for s in range(n_samples):
        cluster = final_labels[s]
        same_cluster = np.where(final_labels == cluster)[0]
        same_cluster = same_cluster[same_cluster != s]
        if len(same_cluster) > 0:
            # Check both train and test consensus
            train_scores = [train_consensus_norm[s, j] for j in same_cluster if train_count[s, j] > 0]
            test_scores = [test_consensus_norm[s, j] for j in same_cluster if test_count[s, j] > 0]
            if train_scores and test_scores:
                avg_train = np.mean(train_scores)
                avg_test = np.mean(test_scores)
                if avg_train > 0.7 and avg_test > 0.7:
                    consistent_count += 1

    result = {
        'labels': pd.Series(final_labels, index=expression_df.index, name='cluster'),
        'train_consensus': train_consensus_norm,
        'test_consensus': test_consensus_norm,
        'combined_consensus': combined_consensus,
        'consistent_count': consistent_count,
    }

    print(f"Consistently classified: {consistent_count}/{n_samples} samples")

    return result
```

---

## Phase 4: Batch Correction

### 4.1 Harmony Integration

```python
def run_harmony(adata, batch_key, n_pcs=30, random_state=0):
    """Batch correction using Harmony.

    Args:
        adata: AnnData with PCA computed
        batch_key: Column in adata.obs with batch information
        n_pcs: Number of PCs to correct
    """
    import harmonypy

    # Run Harmony on PCA
    ho = harmonypy.run_harmony(
        adata.obsm['X_pca'][:, :n_pcs],
        adata.obs,
        batch_key,
        random_state=random_state
    )

    # Store corrected PCs (Z_corr is already n_cells x n_pcs)
    corrected = ho.Z_corr if ho.Z_corr.shape[0] == adata.n_obs else ho.Z_corr.T
    adata.obsm['X_pca_harmony'] = corrected

    # Recompute neighbors on corrected PCs
    sc.pp.neighbors(adata, use_rep='X_pca_harmony', random_state=random_state)

    return adata
```

### 4.2 Combat Batch Correction

```python
def run_combat(adata, batch_key):
    """Batch correction using ComBat (built into scanpy)."""
    sc.pp.combat(adata, key=batch_key)
    return adata
```

---

## Phase 5: Differential Expression Analysis

### 5.1 Scanpy Rank Genes Groups (for scRNA-seq)

```python
def run_de_scanpy(adata, groupby, groups='all', reference='rest',
                  method='wilcoxon', n_genes=None, corr_method='benjamini-hochberg'):
    """Differential expression using scanpy's rank_genes_groups.

    Args:
        adata: AnnData (should be normalized, log-transformed)
        groupby: Column in adata.obs to group by (e.g., 'cell_type', 'condition')
        groups: Which groups to test ('all' or list of specific groups)
        reference: Reference group ('rest' or specific group name)
        method: 'wilcoxon', 't-test', 't-test_overestim_var', 'logreg'
        n_genes: Number of top genes per group (None = all)
        corr_method: Multiple testing correction

    Returns:
        dict: Results per group with gene names, scores, pvals, logfoldchanges
    """
    if n_genes is None:
        n_genes = adata.n_vars

    sc.tl.rank_genes_groups(adata, groupby=groupby, groups=groups,
                            reference=reference, method=method,
                            n_genes=n_genes, corr_method=corr_method)

    # Extract results as DataFrames
    result = {}
    groups_found = adata.uns['rank_genes_groups']['names'].dtype.names

    for group in groups_found:
        df = sc.get.rank_genes_groups_df(adata, group=group)
        result[group] = df
        n_sig = (df['pvals_adj'] < 0.05).sum()
        print(f"  {group}: {n_sig} significant DEGs (padj < 0.05)")

    return result
```

### 5.2 Per-Cell-Type DE Between Conditions

This is the most common pattern in BixBench single-cell questions: comparing conditions within each cell type.

```python
def per_celltype_de(adata, celltype_col, condition_col,
                     treatment, control, method='wilcoxon',
                     padj_threshold=0.05, lfc_threshold=0.0):
    """Run DE analysis for each cell type between two conditions.

    Args:
        adata: AnnData with normalized data
        celltype_col: Column for cell type labels
        condition_col: Column for condition (treatment/control)
        treatment: Treatment condition name
        control: Control condition name
        method: DE method
        padj_threshold: Significance threshold
        lfc_threshold: Minimum absolute log fold change

    Returns:
        dict: {cell_type: DE_results_DataFrame}
    """
    results = {}
    cell_types = adata.obs[celltype_col].unique()

    for ct in cell_types:
        # Subset to this cell type
        mask = adata.obs[celltype_col] == ct
        adata_ct = adata[mask].copy()

        # Check we have cells in both conditions
        n_treatment = (adata_ct.obs[condition_col] == treatment).sum()
        n_control = (adata_ct.obs[condition_col] == control).sum()

        if n_treatment < 3 or n_control < 3:
            print(f"  {ct}: Skipped (treatment={n_treatment}, control={n_control})")
            continue

        # Run DE
        try:
            sc.tl.rank_genes_groups(adata_ct, groupby=condition_col,
                                     groups=[treatment], reference=control,
                                     method=method)

            df = sc.get.rank_genes_groups_df(adata_ct, group=treatment)

            # Filter
            sig = df[(df['pvals_adj'] < padj_threshold) &
                     (df['logfoldchanges'].abs() > lfc_threshold)]

            results[ct] = {
                'all': df,
                'significant': sig,
                'n_sig': len(sig),
                'n_up': (sig['logfoldchanges'] > 0).sum(),
                'n_down': (sig['logfoldchanges'] < 0).sum(),
            }

            print(f"  {ct}: {len(sig)} DEGs ({results[ct]['n_up']} up, {results[ct]['n_down']} down)")
        except Exception as e:
            print(f"  {ct}: DE failed - {e}")

    return results
```

### 5.3 DESeq2-based DE (for pseudo-bulk or bulk-like comparisons)

When cell type data is pre-aggregated or the question specifies DESeq2:

```python
def pseudobulk_deseq2(adata, celltype_col, condition_col, sample_col,
                       contrast=None, padj_threshold=0.05, lfc_threshold=0.0,
                       lfc_shrink=False):
    """Pseudo-bulk DE analysis using DESeq2 (via PyDESeq2).

    Aggregates counts per sample per cell type, then runs DESeq2.
    """
    from pydeseq2.dds import DeseqDataSet
    from pydeseq2.ds import DeseqStats

    results = {}
    cell_types = adata.obs[celltype_col].unique()

    for ct in cell_types:
        mask = adata.obs[celltype_col] == ct
        adata_ct = adata[mask]

        # Aggregate counts per sample
        samples = adata_ct.obs[sample_col].unique()
        if len(samples) < 4:
            continue

        # Build pseudo-bulk counts
        from scipy.sparse import issparse
        X = adata_ct.raw.X if adata_ct.raw is not None else adata_ct.X

        counts_list = []
        meta_list = []
        for s in samples:
            s_mask = adata_ct.obs[sample_col] == s
            x = X[s_mask]
            if issparse(x):
                x = x.toarray()
            counts_list.append(x.sum(axis=0))
            meta_list.append({
                sample_col: s,
                condition_col: adata_ct.obs.loc[s_mask, condition_col].iloc[0]
            })

        counts_df = pd.DataFrame(
            np.array(counts_list),
            index=samples,
            columns=adata_ct.var_names if adata_ct.raw is None else adata_ct.raw.var_names
        ).astype(int)
        meta_df = pd.DataFrame(meta_list).set_index(sample_col)

        # Run DESeq2
        try:
            dds = DeseqDataSet(
                counts=counts_df, metadata=meta_df,
                design=f"~{condition_col}", quiet=True
            )
            dds.deseq2()

            if contrast is not None:
                stat_res = DeseqStats(dds, contrast=contrast, quiet=True)
            else:
                conditions = meta_df[condition_col].unique()
                stat_res = DeseqStats(dds, contrast=[condition_col, conditions[0], conditions[1]], quiet=True)

            stat_res.run_wald_test()
            stat_res.summary()

            if lfc_shrink:
                factor, num, den = contrast or [condition_col, conditions[0], conditions[1]]
                coeff = f"{factor}[T.{num}]"
                try:
                    stat_res.lfc_shrink(coeff=coeff)
                except Exception:
                    pass

            res_df = stat_res.results_df
            sig = res_df[(res_df['padj'] < padj_threshold) &
                          (res_df['log2FoldChange'].abs() > lfc_threshold)]

            results[ct] = {
                'all': res_df,
                'significant': sig,
                'n_sig': len(sig),
            }
            print(f"  {ct}: {len(sig)} DEGs (DESeq2)")
        except Exception as e:
            print(f"  {ct}: DESeq2 failed - {e}")

    return results
```

---

## Phase 6: Statistical Analysis on Expression Data

### 6.1 Gene-Expression Correlation Analysis

For BixBench questions about correlation between gene properties and expression.

```python
def gene_expression_correlation(adata, gene_property_col, expression_values=None,
                                 method='pearson', gene_filter=None):
    """Compute correlation between a gene property and expression levels.

    Args:
        adata: AnnData object
        gene_property_col: Column in adata.var (e.g., 'gene_length')
        expression_values: Pre-computed expression values per gene (optional)
        method: 'pearson' or 'spearman'
        gene_filter: Dict for filtering genes (e.g., {'gene_type': 'protein_coding'})

    Returns:
        dict with correlation, p_value, n_genes
    """
    from scipy.sparse import issparse

    # Get gene property values
    if gene_property_col in adata.var.columns:
        gene_prop = adata.var[gene_property_col]
    else:
        raise ValueError(f"Column '{gene_property_col}' not found in adata.var")

    # Get mean expression per gene
    if expression_values is None:
        X = adata.X.toarray() if issparse(adata.X) else adata.X
        expression_values = pd.Series(np.mean(X, axis=0), index=adata.var_names)

    # Apply gene filter
    if gene_filter is not None:
        mask = pd.Series(True, index=adata.var_names)
        for col, val in gene_filter.items():
            if col in adata.var.columns:
                mask &= adata.var[col] == val
        gene_prop = gene_prop[mask]
        expression_values = expression_values[mask]

    # Remove NaN
    valid = gene_prop.notna() & expression_values.notna()
    gene_prop = gene_prop[valid]
    expression_values = expression_values[valid]

    # Compute correlation
    if method == 'pearson':
        corr, pval = stats.pearsonr(gene_prop.values, expression_values.values)
    elif method == 'spearman':
        corr, pval = stats.spearmanr(gene_prop.values, expression_values.values)

    result = {
        'correlation': corr,
        'p_value': pval,
        'n_genes': len(gene_prop),
        'method': method,
    }

    print(f"{method.capitalize()} r = {corr:.6f}, p = {pval:.2e}, n = {len(gene_prop)} genes")
    return result
```

### 6.2 Per-Cell-Type Correlation

```python
def per_celltype_correlation(adata, celltype_col, gene_property_col,
                              method='pearson', gene_filter=None):
    """Compute gene property vs expression correlation for each cell type.

    Args:
        adata: AnnData
        celltype_col: Column for cell type (in obs)
        gene_property_col: Column for gene property (in var)
        method: 'pearson' or 'spearman'
        gene_filter: Gene filter dict

    Returns:
        dict: {cell_type: {correlation, p_value, n_genes}}
    """
    from scipy.sparse import issparse

    results = {}
    cell_types = adata.obs[celltype_col].unique()

    for ct in cell_types:
        mask = adata.obs[celltype_col] == ct
        adata_ct = adata[mask]

        X = adata_ct.X.toarray() if issparse(adata_ct.X) else adata_ct.X
        mean_expr = pd.Series(np.mean(X, axis=0), index=adata_ct.var_names)

        result = gene_expression_correlation(
            adata_ct, gene_property_col, expression_values=mean_expr,
            method=method, gene_filter=gene_filter
        )
        results[ct] = result

    return results
```

### 6.3 T-Tests Between Groups

```python
def compare_groups_ttest(values1, values2, test='welch'):
    """Compare two groups using t-test.

    Args:
        values1, values2: Arrays of values to compare
        test: 'welch' (unequal variance), 'student' (equal variance), 'paired'

    Returns:
        dict with t_statistic, p_value, df, n1, n2
    """
    values1 = np.asarray(values1, dtype=float)
    values2 = np.asarray(values2, dtype=float)

    # Remove NaN
    values1 = values1[~np.isnan(values1)]
    values2 = values2[~np.isnan(values2)]

    if test == 'welch':
        t_stat, p_val = stats.ttest_ind(values1, values2, equal_var=False)
    elif test == 'student':
        t_stat, p_val = stats.ttest_ind(values1, values2, equal_var=True)
    elif test == 'paired':
        t_stat, p_val = stats.ttest_rel(values1, values2)

    result = {
        't_statistic': t_stat,
        'p_value': p_val,
        'n1': len(values1),
        'n2': len(values2),
        'mean1': np.mean(values1),
        'mean2': np.mean(values2),
    }

    print(f"t = {t_stat:.4f}, p = {p_val:.4e}, n1={len(values1)}, n2={len(values2)}")
    return result
```

### 6.4 ANOVA Across Groups

```python
def anova_across_groups(data_dict):
    """One-way ANOVA across multiple groups.

    Args:
        data_dict: {group_name: array_of_values}

    Returns:
        dict with f_statistic, p_value, group_stats
    """
    groups = list(data_dict.values())
    # Remove NaN from each group
    groups = [np.asarray(g, dtype=float) for g in groups]
    groups = [g[~np.isnan(g)] for g in groups]

    f_stat, p_val = stats.f_oneway(*groups)

    group_stats = {}
    for name, values in data_dict.items():
        values = np.asarray(values, dtype=float)
        values = values[~np.isnan(values)]
        group_stats[name] = {
            'mean': np.mean(values),
            'std': np.std(values),
            'n': len(values),
        }

    result = {
        'f_statistic': f_stat,
        'p_value': p_val,
        'n_groups': len(groups),
        'group_stats': group_stats,
    }

    print(f"F = {f_stat:.4f}, p = {p_val:.4e}, {len(groups)} groups")
    return result
```

### 6.5 Fold Change Analysis

```python
def compute_fold_changes(adata, condition_col, group1, group2,
                          log2=True, gene_filter=None):
    """Compute fold changes between two conditions.

    Args:
        adata: AnnData with expression data
        condition_col: Column to split by
        group1: Numerator group
        group2: Denominator group
        log2: Return log2 fold changes
        gene_filter: Optional gene filter dict

    Returns:
        pd.Series: log2FC per gene
    """
    from scipy.sparse import issparse

    mask1 = adata.obs[condition_col] == group1
    mask2 = adata.obs[condition_col] == group2

    X1 = adata[mask1].X
    X2 = adata[mask2].X

    if issparse(X1):
        X1 = X1.toarray()
    if issparse(X2):
        X2 = X2.toarray()

    mean1 = np.mean(X1, axis=0)
    mean2 = np.mean(X2, axis=0)

    # Pseudocount to avoid division by zero
    pseudocount = 1
    if log2:
        fc = np.log2((mean1 + pseudocount) / (mean2 + pseudocount))
    else:
        fc = mean1 / (mean2 + pseudocount)

    fc_series = pd.Series(fc, index=adata.var_names, name='log2FC')

    if gene_filter is not None:
        mask = pd.Series(True, index=adata.var_names)
        for col, val in gene_filter.items():
            if col in adata.var.columns:
                mask &= adata.var[col] == val
        fc_series = fc_series[mask]

    return fc_series
```

### 6.6 Multiple Testing Correction

```python
def apply_correction(pvalues, method='fdr_bh'):
    """Apply multiple testing correction.

    Args:
        pvalues: Array of p-values
        method: 'fdr_bh' (BH), 'bonferroni', 'fdr_by' (BY), 'holm'

    Returns:
        adjusted p-values
    """
    from statsmodels.stats.multitest import multipletests

    pvals = np.asarray(pvalues, dtype=float)
    mask = ~np.isnan(pvals)
    adjusted = np.full_like(pvals, np.nan)

    if mask.sum() > 0:
        _, adjusted[mask], _, _ = multipletests(pvals[mask], method=method)

    return adjusted
```

---

## Phase 7: Cell Type Annotation

### 7.1 Marker-Based Annotation

```python
def annotate_by_markers(adata, marker_dict, cluster_col='leiden'):
    """Annotate clusters using known marker genes.

    Args:
        adata: AnnData with clustering
        marker_dict: {cell_type: [marker_genes]}
        cluster_col: Column with cluster labels

    Returns:
        adata: With cell_type annotation in obs
    """
    from scipy.sparse import issparse

    # Score each cluster for each cell type
    X = adata.X.toarray() if issparse(adata.X) else adata.X
    expr_df = pd.DataFrame(X, index=adata.obs_names, columns=adata.var_names)

    cluster_scores = {}
    for ct, markers in marker_dict.items():
        available_markers = [m for m in markers if m in adata.var_names]
        if available_markers:
            scores = expr_df[available_markers].mean(axis=1)
            cluster_scores[ct] = scores.groupby(adata.obs[cluster_col]).mean()

    # Assign cell types
    if cluster_scores:
        score_df = pd.DataFrame(cluster_scores)
        assignments = score_df.idxmax(axis=1)
        adata.obs['cell_type_predicted'] = adata.obs[cluster_col].map(assignments)

    return adata
```

### 7.2 ToolUniverse-Based Annotation

Use HPA and cell marker databases for annotation support:

```python
def get_marker_genes_from_tu(cell_type_name, tissue='blood'):
    """Query ToolUniverse for known marker genes of a cell type.

    Uses:
        - HPA_search_genes_by_query: Search for tissue/cell-type markers
        - HPA_get_rna_expression_in_specific_tissues: Validate expression
    """
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    markers = []

    # Search HPA for cell-type specific genes
    try:
        result = tu.tools.HPA_search_genes_by_query(query=f"{cell_type_name} marker {tissue}")
        if result and isinstance(result, list):
            markers.extend([g.get('gene_name', g.get('Gene', '')) for g in result[:20]])
    except Exception:
        pass

    return markers
```

---

## Phase 8: Enrichment Integration

### 8.1 Run Enrichment on DE Results

```python
def run_enrichment_on_degs(gene_list, organism='human',
                           libraries=None, p_cutoff=0.05):
    """Run enrichment analysis on DEG lists using gseapy.

    Args:
        gene_list: List of gene symbols
        organism: Organism name
        libraries: List of Enrichr libraries (default: GO + KEGG + Reactome)
        p_cutoff: Significance threshold

    Returns:
        dict: {library: enrichment_results_df}
    """
    import gseapy as gp

    if libraries is None:
        libraries = [
            'GO_Biological_Process_2023',
            'GO_Molecular_Function_2023',
            'GO_Cellular_Component_2023',
            'KEGG_2021_Human',
            'Reactome_2022',
        ]

    results = {}
    for lib in libraries:
        try:
            enr = gp.enrich(
                gene_list=list(gene_list),
                gene_sets=lib,
                outdir=None,
                no_plot=True,
            )
            df = enr.results
            sig = df[df['Adjusted P-value'] < p_cutoff]
            results[lib] = sig
            print(f"  {lib}: {len(sig)} significant terms")
        except Exception as e:
            print(f"  {lib}: Failed - {e}")

    return results
```

---

## Phase 9: Report Generation and Answer Extraction

### 9.1 Generate Analysis Report

```python
def generate_report(analysis_results, question=None):
    """Generate markdown report from analysis results.

    Args:
        analysis_results: Dict with all computed results
        question: Original question (for targeted answer extraction)
    """
    report = []
    report.append("# Single-Cell Analysis Report\n")

    if 'data_info' in analysis_results:
        info = analysis_results['data_info']
        report.append("## Data Summary")
        report.append(f"- Cells/Samples: {info.get('n_obs', 'N/A')}")
        report.append(f"- Genes: {info.get('n_vars', 'N/A')}")
        report.append(f"- Cell types: {info.get('cell_types', 'N/A')}")
        report.append("")

    if 'qc' in analysis_results:
        report.append("## Quality Control")
        report.append(f"- Cells after QC: {analysis_results['qc']}")
        report.append("")

    if 'de_results' in analysis_results:
        report.append("## Differential Expression Results")
        de = analysis_results['de_results']
        report.append(f"| Cell Type | N DEGs | Up | Down |")
        report.append(f"|-----------|--------|-----|------|")
        for ct, res in de.items():
            report.append(f"| {ct} | {res['n_sig']} | {res.get('n_up', 'N/A')} | {res.get('n_down', 'N/A')} |")
        report.append("")

    if 'correlation_results' in analysis_results:
        report.append("## Correlation Analysis")
        corr = analysis_results['correlation_results']
        if isinstance(corr, dict) and 'correlation' in corr:
            report.append(f"- Correlation: {corr['correlation']:.6f}")
            report.append(f"- P-value: {corr['p_value']:.2e}")
        elif isinstance(corr, dict):
            report.append(f"| Cell Type | Correlation | P-value |")
            report.append(f"|-----------|------------|---------|")
            for ct, res in corr.items():
                if isinstance(res, dict):
                    report.append(f"| {ct} | {res['correlation']:.6f} | {res['p_value']:.2e} |")
        report.append("")

    if 'pca_results' in analysis_results:
        report.append("## PCA Results")
        pca = analysis_results['pca_results']
        var_ratio = pca.get('variance_ratio', [])
        if len(var_ratio) > 0:
            report.append(f"- PC1: {var_ratio[0]*100:.2f}% variance")
            report.append(f"- PC1+PC2: {sum(var_ratio[:2])*100:.2f}% variance")
            report.append(f"- Top 10 PCs: {sum(var_ratio[:10])*100:.2f}% variance")
        report.append("")

    if 'enrichment_results' in analysis_results:
        report.append("## Enrichment Results")
        for lib, df in analysis_results['enrichment_results'].items():
            report.append(f"\n### {lib}")
            if len(df) > 0:
                report.append(f"| Term | P-value | Adjusted P-value | Genes |")
                report.append(f"|------|---------|------------------|-------|")
                for _, row in df.head(10).iterrows():
                    report.append(f"| {row['Term']} | {row['P-value']:.2e} | {row['Adjusted P-value']:.2e} | {row.get('Genes', 'N/A')} |")
            else:
                report.append("No significant terms found.")
        report.append("")

    return "\n".join(report)
```

---

## Phase 10: Cell-Cell Communication Analysis

**NEW CAPABILITY**: Analyze ligand-receptor interactions between cell types using OmniPath database (integrates CellPhoneDB, CellChatDB, and 100+ other databases).

### 10.1 Get Ligand-Receptor Pairs

Use ToolUniverse OmniPath tools to query validated ligand-receptor interactions:

```python
from tooluniverse import ToolUniverse

def get_ligand_receptor_pairs(proteins=None, databases=None):
    """Get ligand-receptor pairs from OmniPath (CellPhoneDB/CellChatDB data).

    Args:
        proteins: List of protein names to filter (None = get all)
        databases: List of source databases (None = all)

    Returns:
        DataFrame with columns: source_genesymbol, target_genesymbol,
                               is_directed, sources, references, curation_effort
    """
    tu = ToolUniverse()
    tu.load_tools()

    # Query OmniPath ligand-receptor interactions
    result = tu.run_tool(
        "OmniPath_get_ligand_receptor_interactions",
        proteins=proteins,  # Comma-separated or None for all
        databases=databases  # e.g., "CellPhoneDB,CellChatDB" or None
    )

    if result['metadata']['success']:
        interactions = result['data']['interactions']
        # Convert to DataFrame
        import pandas as pd
        df = pd.DataFrame(interactions)
        return df
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")
        return pd.DataFrame()

# Example: Get all CellPhoneDB ligand-receptor pairs
lr_pairs = get_ligand_receptor_pairs(databases="CellPhoneDB")
print(f"Found {len(lr_pairs)} L-R pairs from CellPhoneDB")

# Example: Get interactions for specific proteins
immune_lr = get_ligand_receptor_pairs(proteins="CD274,PDCD1,TGFB1,TGFBR2")
print(immune_lr[['source_genesymbol', 'target_genesymbol', 'curation_effort']])
```

### 10.2 Filter to Expressed L-R Pairs

Identify which L-R pairs are expressed in your dataset:

```python
def filter_expressed_lr_pairs(adata, lr_pairs, min_frac=0.1, min_mean=0.1):
    """Filter L-R pairs to only those expressed in the dataset.

    Args:
        adata: AnnData object with normalized expression
        lr_pairs: DataFrame from get_ligand_receptor_pairs()
        min_frac: Minimum fraction of cells expressing (default 0.1 = 10%)
        min_mean: Minimum mean expression level (default 0.1)

    Returns:
        DataFrame with expressed L-R pairs
    """
    # Get gene symbols in dataset
    genes_in_data = set(adata.var_names)

    # Filter L-R pairs to expressed genes
    expressed_lr = lr_pairs[
        lr_pairs['source_genesymbol'].isin(genes_in_data) &
        lr_pairs['target_genesymbol'].isin(genes_in_data)
    ].copy()

    # Calculate expression statistics
    expressed_lr['ligand_mean'] = expressed_lr['source_genesymbol'].apply(
        lambda g: adata[:, g].X.mean() if g in genes_in_data else 0
    )
    expressed_lr['receptor_mean'] = expressed_lr['target_genesymbol'].apply(
        lambda g: adata[:, g].X.mean() if g in genes_in_data else 0
    )
    expressed_lr['ligand_frac'] = expressed_lr['source_genesymbol'].apply(
        lambda g: (adata[:, g].X > 0).mean() if g in genes_in_data else 0
    )
    expressed_lr['receptor_frac'] = expressed_lr['target_genesymbol'].apply(
        lambda g: (adata[:, g].X > 0).mean() if g in genes_in_data else 0
    )

    # Filter by expression thresholds
    expressed_lr = expressed_lr[
        (expressed_lr['ligand_mean'] >= min_mean) &
        (expressed_lr['receptor_mean'] >= min_mean) &
        (expressed_lr['ligand_frac'] >= min_frac) &
        (expressed_lr['receptor_frac'] >= min_frac)
    ]

    return expressed_lr

# Example: Filter to expressed pairs
expressed_lr = filter_expressed_lr_pairs(adata, lr_pairs, min_frac=0.05, min_mean=0.05)
print(f"Expressed L-R pairs: {len(expressed_lr)}/{len(lr_pairs)}")
```

### 10.3 Score Cell-Cell Communication

Calculate communication scores between cell types:

```python
def score_cell_communication(adata, lr_pairs, cell_type_col='cell_type',
                             method='mean_product'):
    """Score cell-cell communication for each cell type pair.

    Args:
        adata: AnnData with cell type annotations
        lr_pairs: Expressed L-R pairs from filter_expressed_lr_pairs()
        cell_type_col: Column in adata.obs with cell type labels
        method: 'mean_product' or 'fraction_product'

    Returns:
        DataFrame with columns: sender, receiver, ligand, receptor, score
    """
    import pandas as pd
    import numpy as np

    cell_types = adata.obs[cell_type_col].unique()
    results = []

    for _, row in lr_pairs.iterrows():
        ligand = row['source_genesymbol']
        receptor = row['target_genesymbol']

        # Skip if genes not in data
        if ligand not in adata.var_names or receptor not in adata.var_names:
            continue

        for sender_ct in cell_types:
            for receiver_ct in cell_types:
                # Get sender cells expressing ligand
                sender_cells = adata.obs[cell_type_col] == sender_ct
                ligand_expr = adata[sender_cells, ligand].X

                # Get receiver cells expressing receptor
                receiver_cells = adata.obs[cell_type_col] == receiver_ct
                receptor_expr = adata[receiver_cells, receptor].X

                # Calculate scores
                if method == 'mean_product':
                    ligand_mean = np.mean(ligand_expr)
                    receptor_mean = np.mean(receptor_expr)
                    score = ligand_mean * receptor_mean
                elif method == 'fraction_product':
                    ligand_frac = np.mean(ligand_expr > 0)
                    receptor_frac = np.mean(receptor_expr > 0)
                    ligand_mean = np.mean(ligand_expr[ligand_expr > 0]) if ligand_frac > 0 else 0
                    receptor_mean = np.mean(receptor_expr[receptor_expr > 0]) if receptor_frac > 0 else 0
                    score = ligand_frac * receptor_frac * ligand_mean * receptor_mean

                if score > 0:  # Only keep non-zero interactions
                    results.append({
                        'sender': sender_ct,
                        'receiver': receiver_ct,
                        'ligand': ligand,
                        'receptor': receptor,
                        'ligand_mean': ligand_mean,
                        'receptor_mean': receptor_mean,
                        'score': score,
                        'curation_effort': row.get('curation_effort', 0),
                        'databases': row.get('sources', 'Unknown')
                    })

    return pd.DataFrame(results)

# Example: Score communication between all cell type pairs
communication_scores = score_cell_communication(adata, expressed_lr, cell_type_col='cell_type')

# Find top interactions
top_interactions = communication_scores.nlargest(20, 'score')
print("\nTop 20 cell-cell interactions:")
print(top_interactions[['sender', 'receiver', 'ligand', 'receptor', 'score']])
```

### 10.4 Annotate with CellPhoneDB/CellChatDB Categories

Get pathway and functional annotations for L-R pairs:

```python
def annotate_communication_pathways(lr_pairs):
    """Add CellPhoneDB/CellChatDB pathway and category annotations.

    Args:
        lr_pairs: DataFrame with ligand-receptor pairs

    Returns:
        DataFrame with added columns: pathway, category, role
    """
    from tooluniverse import ToolUniverse

    tu = ToolUniverse()
    tu.load_tools()

    # Annotate each unique protein
    unique_proteins = set(lr_pairs['source_genesymbol']) | set(lr_pairs['target_genesymbol'])

    annotations = {}
    for protein in unique_proteins:
        result = tu.run_tool(
            "OmniPath_get_cell_communication_annotations",
            protein=protein
        )
        if result['metadata']['success'] and result['data']['annotations']:
            annotations[protein] = result['data']['annotations'][0]

    # Add annotations to L-R pairs
    lr_pairs['ligand_pathway'] = lr_pairs['source_genesymbol'].apply(
        lambda p: annotations.get(p, {}).get('pathway', 'Unknown')
    )
    lr_pairs['ligand_category'] = lr_pairs['source_genesymbol'].apply(
        lambda p: annotations.get(p, {}).get('category', 'Unknown')
    )
    lr_pairs['receptor_category'] = lr_pairs['target_genesymbol'].apply(
        lambda p: annotations.get(p, {}).get('category', 'Unknown')
    )

    return lr_pairs

# Example: Annotate pathways
annotated_lr = annotate_communication_pathways(expressed_lr)
print("\nPathways represented:")
print(annotated_lr['ligand_pathway'].value_counts().head(10))
```

### 10.5 Identify Signaling Cascades

Trace downstream signaling from receptor activation:

```python
def get_downstream_signaling(receptor_gene):
    """Get downstream signaling interactions from a receptor.

    Args:
        receptor_gene: Gene symbol of the receptor

    Returns:
        DataFrame with signaling interactions
    """
    from tooluniverse import ToolUniverse
    import pandas as pd

    tu = ToolUniverse()
    tu.load_tools()

    # Get signaling interactions
    result = tu.run_tool(
        "OmniPath_get_signaling_interactions",
        proteins=receptor_gene,
        is_directed=True  # Only directed interactions
    )

    if result['metadata']['success']:
        interactions = result['data']['interactions']
        df = pd.DataFrame(interactions)

        # Filter to interactions where receptor is the source
        df = df[df['source_genesymbol'] == receptor_gene]

        return df[['source_genesymbol', 'target_genesymbol', 'is_stimulation',
                  'is_inhibition', 'sources', 'references']]
    return pd.DataFrame()

# Example: Get TGFBR2 downstream signaling
tgfbr2_signaling = get_downstream_signaling('TGFBR2')
print(f"\nTGFBR2 signals to {len(tgfbr2_signaling)} downstream targets")
print(tgfbr2_signaling.head())

# Get transcription factors in the cascade
tfs = tgfbr2_signaling[tgfbr2_signaling['target_genesymbol'].str.contains('SMAD|JUN|FOS')]
print(f"\nTranscription factors activated: {list(tfs['target_genesymbol'])}")
```

### 10.6 Example: Tumor-Immune Cell Communication

Complete workflow for analyzing T cell exhaustion checkpoints:

```python
# Step 1: Get immune checkpoint L-R pairs
checkpoint_proteins = "CD274,PDCD1,CTLA4,CD80,CD86,HAVCR2,TIGIT,CD96,NECTIN2"
checkpoint_lr = get_ligand_receptor_pairs(proteins=checkpoint_proteins)

# Step 2: Filter to expressed pairs
expressed_checkpoints = filter_expressed_lr_pairs(adata, checkpoint_lr, min_frac=0.05)

# Step 3: Score communication between tumor and T cells
tumor_tcell_comm = communication_scores[
    ((communication_scores['sender'] == 'Tumor') &
     (communication_scores['receiver'].str.contains('T cell|CD4|CD8'))) |
    ((communication_scores['receiver'] == 'Tumor') &
     (communication_scores['sender'].str.contains('T cell|CD4|CD8')))
]

# Step 4: Find top exhaustion signals
exhaustion_pairs = tumor_tcell_comm[
    tumor_tcell_comm['ligand'].isin(['CD274', 'HAVCR2']) |  # PD-L1, TIM-3
    tumor_tcell_comm['receptor'].isin(['PDCD1', 'HAVCR2', 'CTLA4'])  # PD-1, TIM-3, CTLA4
].sort_values('score', ascending=False)

print("\nTop tumor-T cell exhaustion signals:")
print(exhaustion_pairs[['sender', 'receiver', 'ligand', 'receptor', 'score']])

# Step 5: Report findings
print(f"\nCD274 (PD-L1) expression in tumor: {adata[adata.obs.cell_type=='Tumor', 'CD274'].X.mean():.3f}")
print(f"PDCD1 (PD-1) expression in T cells: {adata[adata.obs.cell_type.str.contains('T cell'), 'PDCD1'].X.mean():.3f}")
```

### 10.7 Handle Protein Complexes

Many receptors are multi-subunit complexes (e.g., TGF-beta receptors):

```python
def check_complex_expression(adata, complex_name, cell_type=None):
    """Check if all subunits of a protein complex are expressed.

    Args:
        adata: AnnData object
        complex_name: Name of the complex (e.g., "TGFB1")
        cell_type: Optional cell type to subset to

    Returns:
        dict with complex composition and expression
    """
    from tooluniverse import ToolUniverse
    import numpy as np

    tu = ToolUniverse()
    tu.load_tools()

    # Get complex composition
    result = tu.run_tool("OmniPath_get_complexes", proteins=complex_name)

    if not result['metadata']['success'] or not result['data']['complexes']:
        return {'complex_found': False}

    complexes = result['data']['complexes']

    # Subset to cell type if specified
    if cell_type:
        adata_subset = adata[adata.obs.cell_type == cell_type, :]
    else:
        adata_subset = adata

    results = []
    for complex_info in complexes:
        components = complex_info.get('components_genesymbols', '').split('_')

        # Check expression of all components
        component_expr = {}
        for comp in components:
            if comp in adata_subset.var_names:
                expr = adata_subset[:, comp].X.mean()
                frac = (adata_subset[:, comp].X > 0).mean()
                component_expr[comp] = {'mean': expr, 'fraction': frac}
            else:
                component_expr[comp] = {'mean': 0, 'fraction': 0}

        # Complex is "expressed" if all subunits are expressed
        # Score as minimum of subunit expressions
        min_mean = min([v['mean'] for v in component_expr.values()])
        min_frac = min([v['fraction'] for v in component_expr.values()])

        results.append({
            'complex_name': complex_info.get('name', 'Unknown'),
            'components': components,
            'component_expression': component_expr,
            'complex_score': min_mean * min_frac,
            'all_subunits_expressed': all([v['fraction'] > 0.1 for v in component_expr.values()])
        })

    return results

# Example: Check TGF-beta receptor complex
tgfb_receptor = check_complex_expression(adata, "TGFBR2", cell_type="Fibroblast")
print("\nTGF-beta receptor complex analysis:")
for comp_result in tgfb_receptor:
    print(f"Complex: {comp_result['complex_name']}")
    print(f"Components: {comp_result['components']}")
    print(f"All subunits expressed: {comp_result['all_subunits_expressed']}")
    print(f"Complex score: {comp_result['complex_score']:.4f}")
```

### 10.8 Visualization

Generate communication network plots:

```python
def plot_communication_network(communication_scores, top_n=50, min_score=0.01):
    """Plot cell-cell communication network.

    Args:
        communication_scores: DataFrame from score_cell_communication()
        top_n: Number of top interactions to show
        min_score: Minimum score threshold
    """
    import matplotlib.pyplot as plt
    import networkx as nx

    # Filter and get top interactions
    comm_filtered = communication_scores[communication_scores['score'] >= min_score]
    comm_top = comm_filtered.nlargest(top_n, 'score')

    # Build network
    G = nx.DiGraph()
    for _, row in comm_top.iterrows():
        edge_label = f"{row['ligand']}→{row['receptor']}"
        G.add_edge(row['sender'], row['receiver'],
                  weight=row['score'], label=edge_label)

    # Plot
    plt.figure(figsize=(12, 10))
    pos = nx.spring_layout(G, k=2, iterations=50)

    # Draw nodes
    nx.draw_networkx_nodes(G, pos, node_size=3000, node_color='lightblue', alpha=0.9)
    nx.draw_networkx_labels(G, pos, font_size=10, font_weight='bold')

    # Draw edges with width proportional to score
    edges = G.edges()
    weights = [G[u][v]['weight'] for u, v in edges]
    max_weight = max(weights)
    widths = [5 * w / max_weight for w in weights]

    nx.draw_networkx_edges(G, pos, width=widths, alpha=0.6,
                          edge_color='gray', arrows=True, arrowsize=20)

    plt.title(f"Cell-Cell Communication Network (Top {top_n} Interactions)", fontsize=14)
    plt.axis('off')
    plt.tight_layout()
    return plt

# Example usage
plot = plot_communication_network(communication_scores, top_n=30)
plot.savefig('cell_communication_network.png', dpi=300, bbox_inches='tight')
```

### 10.9 Complete Cell Communication Report

Generate comprehensive communication analysis report:

```python
def generate_communication_report(adata, cell_type_col='cell_type',
                                 databases="CellPhoneDB,CellChatDB",
                                 min_score=0.01):
    """Generate complete cell-cell communication analysis report.

    Returns:
        Markdown formatted report string
    """
    report = []
    report.append("# Cell-Cell Communication Analysis Report\n")

    # Step 1: Get L-R pairs
    report.append("## 1. Ligand-Receptor Database Query")
    lr_pairs = get_ligand_receptor_pairs(databases=databases)
    report.append(f"- Total L-R pairs in database: {len(lr_pairs)}")
    report.append(f"- Databases: {databases}\n")

    # Step 2: Filter to expressed
    report.append("## 2. Expressed Ligand-Receptor Pairs")
    expressed_lr = filter_expressed_lr_pairs(adata, lr_pairs, min_frac=0.05, min_mean=0.05)
    report.append(f"- Expressed L-R pairs: {len(expressed_lr)}/{len(lr_pairs)} ({100*len(expressed_lr)/len(lr_pairs):.1f}%)")
    report.append(f"- Expression threshold: >5% cells, mean >0.05\n")

    # Step 3: Score communication
    report.append("## 3. Cell-Cell Communication Scores")
    communication_scores = score_cell_communication(adata, expressed_lr, cell_type_col=cell_type_col)
    communication_scores = communication_scores[communication_scores['score'] >= min_score]
    report.append(f"- Total interactions scored: {len(communication_scores)}")
    report.append(f"- Minimum score threshold: {min_score}\n")

    # Top interactions table
    report.append("### Top 20 Interactions")
    report.append("| Sender | Receiver | Ligand | Receptor | Score | Curation |")
    report.append("|--------|----------|--------|----------|-------|----------|")
    top_20 = communication_scores.nlargest(20, 'score')
    for _, row in top_20.iterrows():
        report.append(f"| {row['sender']} | {row['receiver']} | {row['ligand']} | {row['receptor']} | {row['score']:.4f} | {row['curation_effort']} |")
    report.append("")

    # Communication summary by cell type
    report.append("## 4. Communication Summary by Cell Type")
    sender_counts = communication_scores.groupby('sender').size().sort_values(ascending=False)
    receiver_counts = communication_scores.groupby('receiver').size().sort_values(ascending=False)

    report.append("\n### Top Sender Cell Types")
    report.append("| Cell Type | Outgoing Interactions |")
    report.append("|-----------|----------------------|")
    for ct, count in sender_counts.head(10).items():
        report.append(f"| {ct} | {count} |")

    report.append("\n### Top Receiver Cell Types")
    report.append("| Cell Type | Incoming Interactions |")
    report.append("|-----------|----------------------|")
    for ct, count in receiver_counts.head(10).items():
        report.append(f"| {ct} | {count} |")

    # Pathway analysis
    report.append("\n## 5. Pathway Analysis")
    annotated = annotate_communication_pathways(expressed_lr)
    pathway_counts = annotated['ligand_pathway'].value_counts()
    report.append("\n| Pathway | L-R Pairs |")
    report.append("|---------|-----------|")
    for pathway, count in pathway_counts.head(10).items():
        report.append(f"| {pathway} | {count} |")

    return "\n".join(report)

# Example: Generate full report
communication_report = generate_communication_report(adata, cell_type_col='cell_type')
print(communication_report)

# Save to file
with open('cell_communication_report.md', 'w') as f:
    f.write(communication_report)
```

---

## Tool Parameter Reference

**Critical Parameter Notes** (from testing):

| Tool | Parameter | CORRECT Name | Common Mistake |
|------|-----------|--------------|----------------|
| HPA_search_genes_by_query | `query` | query (string) | gene_name |
| HPA_get_rna_expression_in_specific_tissues | `ensembl_id`, `tissue_name` | ensembl_id + tissue_name | gene_name |
| HPA_get_comprehensive_gene_details_by_ensembl_id | ALL 5 params | ensembl_id + 4 booleans | Missing booleans |
| MyGene_query_genes | `query` | query (string) | q |
| MyGene_batch_query | `gene_ids` | gene_ids (list) | ids |
| ensembl_lookup_gene | `gene_id`, `species` | gene_id + species='homo_sapiens' | Missing species |
| UniProt_get_function_by_accession | `accession` | accession (string) | uniprot_id |
| PANTHER_enrichment | `gene_list`, `organism`, `annotation_dataset` | comma-separated string + 9606 | array |
| STRING_functional_enrichment | `protein_ids`, `species` | array + 9606 | single string |

**Response Format Notes**:
- **HPA tools**: Various formats, always check response structure
- **MyGene_query_genes**: `{hits: [{_id, symbol, ensembl, ...}]}`
- **PANTHER_enrichment**: `{data: {enriched_terms: [{...}]}}`
- **STRING_functional_enrichment**: Direct list of enrichment results

---

## Fallback Strategies

### Data Loading
- **Primary**: `sc.read_h5ad()` for h5ad files
- **Fallback**: `pd.read_csv()` + convert to AnnData
- **Default**: Try multiple delimiters (tab, comma) and orientations

### Differential Expression
- **Primary**: `sc.tl.rank_genes_groups()` (Wilcoxon)
- **Fallback**: Manual Wilcoxon/t-test via scipy.stats
- **Default**: Fold change computation without p-values

### Enrichment
- **Primary**: gseapy Enrichr
- **Fallback**: PANTHER via ToolUniverse
- **Default**: STRING functional enrichment via ToolUniverse

### Gene Annotation
- **Primary**: Gene info from h5ad/var columns
- **Fallback**: MyGene_query_genes via ToolUniverse
- **Default**: Ensembl via ToolUniverse

---

## Common Use Patterns

### Pattern 1: Per-Cell-Type Differential Expression
```
Input: h5ad file with cell type annotations + two conditions
Workflow: Load -> Subset by cell type -> DE per cell type -> Report
Output: Table of DEGs per cell type, counts, top genes
Example: bix-33 (immune cell types with most DEGs after treatment)
```

### Pattern 2: Gene Property vs Expression Correlation by Cell Type
```
Input: Expression data + gene annotations (gene length, biotype)
Workflow: Load -> Filter genes -> Per-cell-type mean expression -> Correlate
Output: Correlation coefficients and p-values per cell type
Example: bix-22 (gene length vs expression by immune cell type)
```

### Pattern 3: Cell-Type Comparison Statistics
```
Input: DE results per cell type
Workflow: Run DE -> Extract LFCs per cell type -> t-test/ANOVA between groups
Output: t-statistic, F-statistic, p-value
Example: bix-31 (t-test comparing LFCs between CD4/CD8 and other cell types)
```

### Pattern 4: Expression Clustering and PCA
```
Input: Expression matrix (samples x genes)
Workflow: Transform -> PCA -> Variance explained / Clustering -> Enrichment
Output: PC variance, cluster assignments, enriched pathways per cluster
Example: bix-27 (PCA variance explained, bootstrap consensus clustering)
```

### Pattern 5: miRNA / Small RNA Analysis
```
Input: miRNA expression matrix + cell type metadata
Workflow: Load -> Fold changes -> ANOVA/t-test across cell types -> Corrections
Output: F-statistics, p-values, fold change distributions
Example: bix-36 (ANOVA comparing miRNA expression across immune cell types)
```

### Pattern 6: Full scRNA-seq Pipeline
```
Input: Raw count matrix (10X or h5ad)
Workflow: QC -> Normalize -> HVG -> PCA -> Neighbors -> Cluster -> Annotate -> DE
Output: Annotated clusters, marker genes, DEGs
```

---

## Quality Checks

### Data Completeness
- [ ] Input data loaded successfully with correct orientation
- [ ] Metadata aligned with expression data
- [ ] Gene annotations loaded if needed (gene length, biotype)
- [ ] Cell type annotations present if needed

### Statistical Validity
- [ ] Appropriate statistical test for question type
- [ ] Multiple testing correction applied when needed
- [ ] Sufficient sample size per group (>= 3)
- [ ] NaN values handled properly

### Report Quality
- [ ] Specific answer extracted for the question asked
- [ ] Numbers rounded to requested precision
- [ ] Units and scales correct (log2, log10, percentage, etc.)
- [ ] All cell types / conditions accounted for

---

## Limitations & Known Issues

### Package-Specific
- **scanpy**: Leiden clustering requires leidenalg package
- **harmonypy**: May have numerical issues with very small batches
- **gseapy**: organism parameter removed in v1.1+, organism is encoded in library name
- **PyDESeq2**: ref_level deprecated in v0.5.4, use pd.Categorical instead

### Analysis-Specific
- **Pseudo-bulk DE**: Requires sufficient cells per sample per cell type
- **Marker-based annotation**: Only as good as the marker gene lists
- **Bootstrap clustering**: Can be slow for large datasets (>1000 samples)
- **Correlation analysis**: Pearson assumes linearity, Spearman for non-linear

### Data-Specific
- **h5ad loading**: Large files may require chunked loading
- **10X files**: Feature barcode format changed between CellRanger versions
- **Gene names**: May need mapping between Ensembl IDs and symbols

---

## Summary

**Single-Cell Genomics Skill** provides:
1. Complete scRNA-seq pipeline (QC, normalization, PCA, clustering, DE)
2. Per-cell-type differential expression with multiple methods (Wilcoxon, t-test, DESeq2)
3. Gene property correlation analysis by cell type
4. Statistical comparisons between cell populations (t-test, ANOVA, fold changes)
5. Expression matrix clustering (hierarchical, bootstrap consensus)
6. Gene enrichment integration (gseapy, PANTHER, STRING via ToolUniverse)
7. Cell type annotation (marker-based + ToolUniverse databases)
8. Batch correction (Harmony, ComBat)
9. **NEW: Cell-cell communication analysis** (ligand-receptor interactions, signaling cascades, OmniPath/CellPhoneDB/CellChatDB integration)

**BixBench Coverage**: 18+ questions across 5 projects (bix-22, bix-27, bix-31, bix-33, bix-36)

**Outputs**: Direct answers to specific questions + comprehensive markdown reports

**Best for**: Single-cell RNA-seq analysis, cell-type-specific differential expression, cell-cell communication (ligand-receptor, tumor-immune interactions), gene-expression correlation by cell type, expression matrix clustering, immune cell population comparisons
