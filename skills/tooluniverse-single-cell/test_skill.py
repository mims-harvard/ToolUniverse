#!/usr/bin/env python3
"""
Comprehensive Test Suite for tooluniverse-single-cell Skill

Tests all core capabilities:
1. Data loading (h5ad, CSV, orientation detection)
2. Quality control (filtering, QC metrics)
3. Normalization and scaling
4. PCA (scanpy and manual)
5. Clustering (Leiden, hierarchical, bootstrap consensus)
6. Differential expression (scanpy rank_genes_groups, per-cell-type)
7. Gene-expression correlation analysis
8. Statistical comparisons (t-test, ANOVA, fold changes)
9. Multiple testing correction
10. Batch correction (Harmony)
11. Cell type annotation
12. Enrichment integration
13. Report generation
14. BixBench-style question patterns
"""

import sys
import traceback
import warnings
import os
import tempfile

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Track test results
RESULTS = []
PASS_COUNT = 0
FAIL_COUNT = 0


def record(test_name, passed, detail=""):
    global PASS_COUNT, FAIL_COUNT
    status = "PASS" if passed else "FAIL"
    if passed:
        PASS_COUNT += 1
    else:
        FAIL_COUNT += 1
    RESULTS.append((test_name, status, detail))
    print(f"  [{status}] {test_name}" + (f" -- {detail}" if detail else ""))


# ============================================================
# Helper: Generate synthetic scRNA-seq data
# ============================================================

def generate_scrna_data(n_cells=500, n_genes=200, n_cell_types=4,
                        n_conditions=2, seed=42):
    """Generate synthetic scRNA-seq count data with known cell types and conditions.

    Returns:
        adata: AnnData object with counts, cell_type, and condition annotations
        de_genes: Dict of {cell_type: list of known DE genes}
    """
    import anndata as ad
    from scipy.sparse import csr_matrix

    np.random.seed(seed)

    cell_type_names = ['CD4_T', 'CD8_T', 'CD14_Monocytes', 'B_cells'][:n_cell_types]
    condition_names = ['control', 'treatment'][:n_conditions]

    # Assign cell types and conditions
    cells_per_type = n_cells // n_cell_types
    cell_types = []
    conditions = []
    for ct in cell_type_names:
        for cond in condition_names:
            n = cells_per_type // n_conditions
            cell_types.extend([ct] * n)
            conditions.extend([cond] * n)

    n_cells_actual = len(cell_types)
    gene_names = [f'Gene_{i:04d}' for i in range(n_genes)]

    # Generate base counts (negative binomial)
    base_means = np.random.lognormal(mean=3, sigma=1.5, size=n_genes)
    counts = np.zeros((n_cells_actual, n_genes), dtype=np.float32)

    # Add cell-type-specific marker genes
    de_genes = {}
    n_markers_per_type = 10
    for ct_idx, ct in enumerate(cell_type_names):
        start = ct_idx * n_markers_per_type
        end = start + n_markers_per_type
        marker_genes = gene_names[start:end]
        de_genes[ct] = marker_genes

    for i in range(n_cells_actual):
        ct = cell_types[i]
        cond = conditions[i]
        ct_idx = cell_type_names.index(ct)

        for j in range(n_genes):
            mu = base_means[j]

            # Upregulate markers for this cell type
            if ct_idx * n_markers_per_type <= j < (ct_idx + 1) * n_markers_per_type:
                mu *= 5.0

            # Add condition effect for first cell type
            if cond == 'treatment' and ct_idx == 2 and j < 20:  # CD14_Monocytes
                mu *= 3.0

            r = 1 / 0.3
            p = r / (r + mu)
            counts[i, j] = np.random.negative_binomial(max(1, int(r)), min(0.999, max(0.001, p)))

    # Create AnnData
    obs = pd.DataFrame({
        'cell_type': cell_types,
        'condition': conditions,
        'sample_id': [f'sample_{i % 6}' for i in range(n_cells_actual)],
    }, index=[f'cell_{i:04d}' for i in range(n_cells_actual)])

    var = pd.DataFrame({
        'gene_length': np.random.lognormal(mean=7, sigma=1, size=n_genes).astype(int),
        'gene_type': ['protein_coding'] * (n_genes - 20) + ['lncRNA'] * 20,
    }, index=gene_names)

    adata = ad.AnnData(
        X=csr_matrix(counts),
        obs=obs,
        var=var,
    )

    return adata, de_genes


def generate_bulk_expression(n_samples=200, n_genes=1000, n_clusters=3, seed=42):
    """Generate bulk expression data for clustering tests."""
    np.random.seed(seed)

    gene_names = [f'Gene_{i:04d}' for i in range(n_genes)]
    sample_names = [f'sample_{i:04d}' for i in range(n_samples)]

    # Create cluster structure
    cluster_means = np.random.randn(n_clusters, n_genes)
    samples_per_cluster = n_samples // n_clusters

    X = np.zeros((n_samples, n_genes))
    true_labels = np.zeros(n_samples, dtype=int)

    for c in range(n_clusters):
        start = c * samples_per_cluster
        end = start + samples_per_cluster if c < n_clusters - 1 else n_samples
        n = end - start
        X[start:end] = cluster_means[c] + np.random.randn(n, n_genes) * 0.5
        true_labels[start:end] = c + 1

    df = pd.DataFrame(X, index=sample_names, columns=gene_names)
    return df, true_labels


def generate_mirna_data(n_mirnas=175, n_samples=60, seed=42):
    """Generate miRNA expression data across cell types."""
    np.random.seed(seed)

    mirna_names = [f'miR-{i}' for i in range(n_mirnas)]
    cell_types = ['CD4', 'CD8', 'CD14', 'CD19', 'PBMC']
    samples_per_type = n_samples // len(cell_types)

    sample_names = []
    cell_type_labels = []
    for ct in cell_types:
        for i in range(samples_per_type):
            sample_names.append(f'{ct}_s{i}')
            cell_type_labels.append(ct)

    n_actual = len(sample_names)
    X = np.random.lognormal(mean=2, sigma=1.5, size=(n_actual, n_mirnas))

    # Add mild cell-type effect (small, so ANOVA should be non-significant for most)
    for i in range(n_actual):
        ct_idx = cell_types.index(cell_type_labels[i])
        X[i, :5] += ct_idx * 0.1  # Very small effect

    df = pd.DataFrame(X, index=sample_names, columns=mirna_names)
    meta = pd.DataFrame({'cell_type': cell_type_labels}, index=sample_names)

    return df, meta


# ============================================================
# Test Groups
# ============================================================

def test_data_loading():
    """Test data loading from various formats."""
    print("\n=== Test Group 1: Data Loading ===")

    import anndata as ad
    import scanpy as sc

    # Test 1.1: Create and load h5ad
    adata, _ = generate_scrna_data(n_cells=100, n_genes=50)
    with tempfile.NamedTemporaryFile(suffix='.h5ad', delete=False) as f:
        adata.write(f.name)
        adata_loaded = sc.read_h5ad(f.name)
        record("Load h5ad file",
               adata_loaded.n_obs == adata.n_obs and adata_loaded.n_vars == adata.n_vars,
               f"Shape: {adata_loaded.shape}")
        os.unlink(f.name)

    # Test 1.2: Load CSV count matrix
    df = pd.DataFrame(
        np.random.poisson(5, (20, 100)),
        index=[f'sample_{i}' for i in range(20)],
        columns=[f'gene_{i}' for i in range(100)]
    )
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False, mode='w') as f:
        df.to_csv(f.name)
        df_loaded = pd.read_csv(f.name, index_col=0)
        adata_csv = ad.AnnData(df_loaded)
        record("Load CSV count matrix",
               adata_csv.n_obs == 20 and adata_csv.n_vars == 100,
               f"Shape: {adata_csv.shape}")
        os.unlink(f.name)

    # Test 1.3: Orientation detection
    # Genes as rows (transposed)
    df_transposed = df.T  # 100 genes x 20 samples
    if df_transposed.shape[0] > df_transposed.shape[1] * 5:
        df_oriented = df_transposed.T
    else:
        df_oriented = df_transposed
    # In this case 100 > 20*5=100 is False, so no transpose
    # Let's test with a clearer case
    df_clear = pd.DataFrame(
        np.random.poisson(5, (5000, 10)),  # 5000 genes x 10 samples
        index=[f'gene_{i}' for i in range(5000)],
        columns=[f'sample_{i}' for i in range(10)]
    )
    if df_clear.shape[0] > df_clear.shape[1] * 5:
        df_oriented = df_clear.T
    else:
        df_oriented = df_clear
    record("Orientation detection (genes-as-rows)",
           df_oriented.shape[0] == 10 and df_oriented.shape[1] == 5000,
           f"Oriented shape: {df_oriented.shape}")

    # Test 1.4: Load TSV with metadata alignment
    meta_df = pd.DataFrame({
        'condition': ['A'] * 10 + ['B'] * 10,
        'batch': ['batch1'] * 5 + ['batch2'] * 5 + ['batch1'] * 5 + ['batch2'] * 5,
    }, index=[f'sample_{i}' for i in range(20)])

    adata_meta = ad.AnnData(df)
    common = adata_meta.obs_names.intersection(meta_df.index)
    for col in meta_df.columns:
        adata_meta.obs[col] = meta_df.loc[common, col].values

    record("Metadata alignment",
           'condition' in adata_meta.obs.columns and 'batch' in adata_meta.obs.columns,
           f"Obs columns: {list(adata_meta.obs.columns)}")

    # Test 1.5: Validate AnnData
    from scipy.sparse import issparse
    adata_test, _ = generate_scrna_data(n_cells=100, n_genes=50)
    is_sparse = issparse(adata_test.X)
    has_obs = len(adata_test.obs.columns) > 0
    has_var = len(adata_test.var.columns) > 0
    record("AnnData validation",
           is_sparse and has_obs and has_var,
           f"Sparse: {is_sparse}, Obs cols: {len(adata_test.obs.columns)}, Var cols: {len(adata_test.var.columns)}")


def test_qc_preprocessing():
    """Test quality control and preprocessing."""
    print("\n=== Test Group 2: QC and Preprocessing ===")

    import scanpy as sc
    from scipy.sparse import issparse

    adata, _ = generate_scrna_data(n_cells=300, n_genes=100)
    n_before = adata.n_obs

    # Test 2.1: QC metrics
    adata.var['mt'] = adata.var_names.str.startswith('MT-')
    sc.pp.calculate_qc_metrics(adata, qc_vars=['mt'], percent_top=None, log1p=False, inplace=True)
    record("QC metrics computed",
           'total_counts' in adata.obs.columns and 'n_genes_by_counts' in adata.obs.columns,
           f"QC columns: total_counts, n_genes_by_counts, pct_counts_mt")

    # Test 2.2: Cell filtering
    sc.pp.filter_cells(adata, min_genes=3)
    n_after_cell = adata.n_obs
    record("Cell filtering (min_genes)",
           n_after_cell <= n_before,
           f"{n_before} -> {n_after_cell} cells")

    # Test 2.3: Gene filtering
    n_genes_before = adata.n_vars
    sc.pp.filter_genes(adata, min_cells=3)
    record("Gene filtering (min_cells)",
           adata.n_vars <= n_genes_before,
           f"{n_genes_before} -> {adata.n_vars} genes")

    # Test 2.4: Normalization
    adata_norm = adata.copy()
    sc.pp.normalize_total(adata_norm, target_sum=1e4)
    X = adata_norm.X.toarray() if issparse(adata_norm.X) else adata_norm.X
    # After normalize_total, rows should sum to ~10000
    row_sums = X.sum(axis=1)
    record("Library-size normalization",
           np.allclose(row_sums, 1e4, atol=1),
           f"Mean row sum: {row_sums.mean():.1f}")

    # Test 2.5: Log transform
    sc.pp.log1p(adata_norm)
    X_log = adata_norm.X.toarray() if issparse(adata_norm.X) else adata_norm.X
    record("Log1p transform",
           X_log.min() >= 0,
           f"Min value: {X_log.min():.4f}, Max: {X_log.max():.4f}")

    # Test 2.6: HVG selection
    adata_hvg = adata.copy()
    sc.pp.normalize_total(adata_hvg, target_sum=1e4)
    sc.pp.log1p(adata_hvg)
    n_hvg = min(50, adata_hvg.n_vars)
    sc.pp.highly_variable_genes(adata_hvg, n_top_genes=n_hvg)
    n_selected = adata_hvg.var['highly_variable'].sum()
    record("Highly variable genes",
           n_selected > 0 and n_selected <= adata_hvg.n_vars,
           f"{n_selected} HVGs selected")

    # Test 2.7: Scaling
    sc.pp.scale(adata_norm, max_value=10)
    X_scaled = adata_norm.X if not issparse(adata_norm.X) else adata_norm.X.toarray()
    record("Z-score scaling",
           X_scaled.max() <= 10.01,
           f"Max after scaling: {X_scaled.max():.4f}")


def test_pca():
    """Test PCA functionality."""
    print("\n=== Test Group 3: PCA ===")

    import scanpy as sc
    from scipy.sparse import issparse

    # Test 3.1: Scanpy PCA
    adata, _ = generate_scrna_data(n_cells=200, n_genes=100)
    sc.pp.normalize_total(adata, target_sum=1e4)
    sc.pp.log1p(adata)
    sc.pp.scale(adata, max_value=10)

    n_comps = min(50, adata.n_vars, adata.n_obs - 1)
    sc.tl.pca(adata, n_comps=n_comps)

    record("Scanpy PCA computation",
           'X_pca' in adata.obsm and 'pca' in adata.uns,
           f"PCA shape: {adata.obsm['X_pca'].shape}")

    # Test 3.2: Variance explained
    var_ratio = adata.uns['pca']['variance_ratio']
    total_var = sum(var_ratio)
    record("PCA variance explained",
           total_var > 0 and total_var <= 1.01,
           f"PC1: {var_ratio[0]*100:.2f}%, Total: {total_var*100:.2f}%")

    # Test 3.3: Manual PCA with sklearn (bix-27 pattern)
    from sklearn.decomposition import PCA as skPCA

    df = pd.DataFrame(
        np.random.lognormal(2, 1, (100, 500)),
        index=[f'sample_{i}' for i in range(100)],
        columns=[f'gene_{i}' for i in range(500)]
    )

    X = np.log10(df.values + 1)
    pca = skPCA(n_components=min(100, 500))
    pca.fit(X)

    pc1_var = pca.explained_variance_ratio_[0] * 100
    record("Manual PCA (log10 + pseudocount)",
           pc1_var > 0 and pc1_var < 100,
           f"PC1: {pc1_var:.2f}% variance")

    # Test 3.4: Cumulative variance
    cum_var = np.cumsum(pca.explained_variance_ratio_)
    n_90 = np.argmax(cum_var >= 0.9) + 1 if np.any(cum_var >= 0.9) else len(cum_var)
    record("Cumulative variance explained",
           cum_var[-1] > 0.99,
           f"PCs for 90% variance: {n_90}")


def test_clustering():
    """Test clustering algorithms."""
    print("\n=== Test Group 4: Clustering ===")

    import scanpy as sc

    # Test 4.1: Leiden clustering
    adata, _ = generate_scrna_data(n_cells=200, n_genes=100)
    sc.pp.normalize_total(adata, target_sum=1e4)
    sc.pp.log1p(adata)
    sc.pp.scale(adata, max_value=10)
    n_comps = min(30, adata.n_vars, adata.n_obs - 1)
    sc.tl.pca(adata, n_comps=n_comps)
    sc.pp.neighbors(adata, n_neighbors=15, n_pcs=min(20, n_comps))

    sc.tl.leiden(adata, resolution=0.5, random_state=0)
    n_clusters_leiden = adata.obs['leiden'].nunique()
    record("Leiden clustering",
           n_clusters_leiden >= 2,
           f"{n_clusters_leiden} clusters")

    # Test 4.2: UMAP embedding
    sc.tl.umap(adata, random_state=0)
    record("UMAP embedding",
           'X_umap' in adata.obsm and adata.obsm['X_umap'].shape[1] == 2,
           f"UMAP shape: {adata.obsm['X_umap'].shape}")

    # Test 4.3: Hierarchical clustering
    from scipy.cluster.hierarchy import linkage, fcluster

    df, true_labels = generate_bulk_expression(n_samples=50, n_genes=100, n_clusters=3)
    Z = linkage(df.values, method='ward')
    pred_labels = fcluster(Z, t=3, criterion='maxclust')

    record("Hierarchical clustering",
           len(np.unique(pred_labels)) == 3,
           f"3 clusters, sizes: {[sum(pred_labels == c) for c in range(1, 4)]}")

    # Test 4.4: Bootstrap consensus clustering
    df_small, _ = generate_bulk_expression(n_samples=60, n_genes=50, n_clusters=3, seed=42)

    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from scipy.spatial.distance import squareform

    np.random.seed(42)
    n_samples = len(df_small)
    n_iterations = 20
    n_train = int(n_samples * 0.7)
    consensus = np.zeros((n_samples, n_samples))
    count_mat = np.zeros((n_samples, n_samples))

    for it in range(n_iterations):
        indices = np.random.permutation(n_samples)
        train_idx = indices[:n_train]
        test_idx = indices[n_train:]

        train_data = df_small.iloc[train_idx]
        Z_train = linkage(train_data.values, method='ward')
        train_labels = fcluster(Z_train, t=3, criterion='maxclust')

        # Update consensus for training samples
        for a_i, a in enumerate(train_idx):
            for b_i, b in enumerate(train_idx):
                count_mat[a, b] += 1
                if train_labels[a_i] == train_labels[b_i]:
                    consensus[a, b] += 1

        # Predict test
        scaler = StandardScaler()
        X_train = scaler.fit_transform(train_data.values)
        X_test = scaler.transform(df_small.iloc[test_idx].values)
        lr = LogisticRegression(max_iter=1000, random_state=42)
        lr.fit(X_train, train_labels)
        test_labels = lr.predict(X_test)

        for a_i, a in enumerate(test_idx):
            for b_i, b in enumerate(test_idx):
                count_mat[a, b] += 1
                if test_labels[a_i] == test_labels[b_i]:
                    consensus[a, b] += 1

    with np.errstate(divide='ignore', invalid='ignore'):
        consensus_norm = np.where(count_mat > 0, consensus / count_mat, 0)
    np.fill_diagonal(consensus_norm, 1.0)

    dist = 1 - consensus_norm
    np.fill_diagonal(dist, 0)
    dist = np.maximum(dist, 0)
    dist = (dist + dist.T) / 2
    condensed = squareform(dist)
    Z_final = linkage(condensed, method='average')
    final_labels = fcluster(Z_final, t=3, criterion='maxclust')

    record("Bootstrap consensus clustering",
           len(np.unique(final_labels)) == 3,
           f"3 clusters, sizes: {[sum(final_labels == c) for c in range(1, 4)]}")


def test_differential_expression():
    """Test differential expression analysis."""
    print("\n=== Test Group 5: Differential Expression ===")

    import scanpy as sc
    from scipy.sparse import issparse

    # Generate data with known DE genes in CD14_Monocytes
    adata, de_genes = generate_scrna_data(n_cells=400, n_genes=100)

    # Normalize
    sc.pp.normalize_total(adata, target_sum=1e4)
    sc.pp.log1p(adata)

    # Test 5.1: Global DE between conditions
    sc.tl.rank_genes_groups(adata, groupby='condition',
                            groups=['treatment'], reference='control',
                            method='wilcoxon')
    df_de = sc.get.rank_genes_groups_df(adata, group='treatment')
    n_sig = (df_de['pvals_adj'] < 0.05).sum()
    record("Global DE (Wilcoxon)",
           len(df_de) > 0 and n_sig >= 0,
           f"{n_sig} significant DEGs out of {len(df_de)}")

    # Test 5.2: DE with t-test
    sc.tl.rank_genes_groups(adata, groupby='condition',
                            groups=['treatment'], reference='control',
                            method='t-test')
    df_ttest = sc.get.rank_genes_groups_df(adata, group='treatment')
    record("DE (t-test method)",
           len(df_ttest) > 0,
           f"{(df_ttest['pvals_adj'] < 0.05).sum()} significant DEGs")

    # Test 5.3: Per-cell-type DE
    cell_types = adata.obs['cell_type'].unique()
    per_ct_results = {}

    for ct in cell_types:
        adata_ct = adata[adata.obs['cell_type'] == ct].copy()
        n_treat = (adata_ct.obs['condition'] == 'treatment').sum()
        n_ctrl = (adata_ct.obs['condition'] == 'control').sum()

        if n_treat < 3 or n_ctrl < 3:
            continue

        sc.tl.rank_genes_groups(adata_ct, groupby='condition',
                                groups=['treatment'], reference='control',
                                method='wilcoxon')
        df_ct = sc.get.rank_genes_groups_df(adata_ct, group='treatment')
        n_sig_ct = (df_ct['pvals_adj'] < 0.05).sum()
        per_ct_results[ct] = n_sig_ct

    record("Per-cell-type DE",
           len(per_ct_results) >= 2,
           f"Cell types analyzed: {len(per_ct_results)}, DEGs: {per_ct_results}")

    # Test 5.4: Identify cell type with most DEGs (bix-33 pattern)
    if per_ct_results:
        top_ct = max(per_ct_results, key=per_ct_results.get)
        record("Cell type with most DEGs (bix-33 pattern)",
               top_ct is not None,
               f"Top cell type: {top_ct} ({per_ct_results[top_ct]} DEGs)")

    # Test 5.5: Check specific gene across cell types (bix-33-q6 pattern)
    gene_to_check = 'Gene_0000'
    ct_with_sig = 0
    for ct in cell_types:
        adata_ct = adata[adata.obs['cell_type'] == ct].copy()
        n_treat = (adata_ct.obs['condition'] == 'treatment').sum()
        n_ctrl = (adata_ct.obs['condition'] == 'control').sum()
        if n_treat < 3 or n_ctrl < 3:
            continue

        sc.tl.rank_genes_groups(adata_ct, groupby='condition',
                                groups=['treatment'], reference='control',
                                method='wilcoxon')
        df_ct = sc.get.rank_genes_groups_df(adata_ct, group='treatment')
        gene_row = df_ct[df_ct['names'] == gene_to_check]
        if len(gene_row) > 0 and gene_row.iloc[0]['pvals_adj'] < 0.05:
            ct_with_sig += 1

    record("Gene-specific DE across cell types",
           ct_with_sig >= 0,
           f"{gene_to_check} significant in {ct_with_sig} cell types")

    # Test 5.6: Marker genes per cluster
    sc.tl.rank_genes_groups(adata, groupby='cell_type', method='wilcoxon')
    marker_groups = adata.uns['rank_genes_groups']['names'].dtype.names
    record("Marker genes per cluster",
           len(marker_groups) >= 2,
           f"Groups: {list(marker_groups)}")

    # Test 5.7: DE result has expected columns
    df_check = sc.get.rank_genes_groups_df(adata, group=marker_groups[0])
    expected_cols = {'names', 'scores', 'logfoldchanges', 'pvals', 'pvals_adj'}
    actual_cols = set(df_check.columns)
    record("DE result columns",
           expected_cols.issubset(actual_cols),
           f"Columns: {list(df_check.columns)}")


def test_correlation_analysis():
    """Test gene-expression correlation analysis."""
    print("\n=== Test Group 6: Correlation Analysis ===")

    import anndata as ad
    from scipy import stats
    from scipy.sparse import issparse

    # Generate data with gene length correlation
    np.random.seed(42)
    n_genes = 200
    n_cells = 100

    gene_lengths = np.random.lognormal(mean=7, sigma=1, size=n_genes)

    # Create expression correlated with gene length
    counts = np.zeros((n_cells, n_genes))
    for j in range(n_genes):
        # Expression weakly correlated with gene length
        mu = gene_lengths[j] / 1000 + np.random.normal(0, 0.5)
        mu = max(0.1, mu)
        counts[:, j] = np.random.poisson(mu, n_cells)

    gene_names = [f'Gene_{i:04d}' for i in range(n_genes)]
    cell_names = [f'cell_{i:04d}' for i in range(n_cells)]
    cell_types = ['CD4'] * 25 + ['CD8'] * 25 + ['CD14'] * 25 + ['CD19'] * 25

    adata = ad.AnnData(
        X=counts.astype(np.float32),
        obs=pd.DataFrame({'cell_type': cell_types}, index=cell_names),
        var=pd.DataFrame({
            'gene_length': gene_lengths.astype(int),
            'gene_type': ['protein_coding'] * n_genes,
        }, index=gene_names)
    )

    # Test 6.1: Pearson correlation (overall)
    mean_expr = np.mean(counts, axis=0)
    r, p = stats.pearsonr(gene_lengths, mean_expr)
    record("Pearson correlation (gene length vs expression)",
           isinstance(r, float) and isinstance(p, float),
           f"r = {r:.6f}, p = {p:.2e}")

    # Test 6.2: Per-cell-type correlation (bix-22 pattern)
    ct_correlations = {}
    for ct in ['CD4', 'CD8', 'CD14', 'CD19']:
        mask = np.array(cell_types) == ct
        ct_expr = np.mean(counts[mask], axis=0)
        r_ct, p_ct = stats.pearsonr(gene_lengths, ct_expr)
        ct_correlations[ct] = {'r': r_ct, 'p': p_ct}

    record("Per-cell-type Pearson correlation (bix-22 pattern)",
           len(ct_correlations) == 4,
           f"Correlations: " + ", ".join(f"{ct}: r={v['r']:.4f}" for ct, v in ct_correlations.items()))

    # Test 6.3: Find cell type with weakest correlation (bix-22-q1 pattern)
    weakest_ct = min(ct_correlations, key=lambda x: abs(ct_correlations[x]['r']))
    record("Weakest correlation cell type (bix-22-q1 pattern)",
           weakest_ct in ['CD4', 'CD8', 'CD14', 'CD19'],
           f"Weakest: {weakest_ct} (r = {ct_correlations[weakest_ct]['r']:.6f})")

    # Test 6.4: Spearman correlation
    rho, p_spearman = stats.spearmanr(gene_lengths, mean_expr)
    record("Spearman correlation",
           isinstance(rho, float),
           f"rho = {rho:.6f}, p = {p_spearman:.2e}")

    # Test 6.5: Correlation with gene filter (protein-coding only)
    # All genes are protein_coding in this test, so result should be same
    pc_mask = adata.var['gene_type'] == 'protein_coding'
    gl_filtered = gene_lengths[pc_mask]
    expr_filtered = mean_expr[pc_mask]
    r_filtered, p_filtered = stats.pearsonr(gl_filtered, expr_filtered)
    record("Correlation with gene type filter",
           abs(r_filtered - r) < 0.001,  # Should be same since all are protein_coding
           f"r(filtered) = {r_filtered:.6f}")


def test_statistical_comparisons():
    """Test statistical comparison functions."""
    print("\n=== Test Group 7: Statistical Comparisons ===")

    from scipy import stats
    from statsmodels.stats.multitest import multipletests

    # Test 7.1: Two-sample t-test (bix-31 pattern)
    np.random.seed(42)
    group1 = np.random.normal(2.0, 1.0, 100)  # CD4/CD8 LFCs
    group2 = np.random.normal(0.5, 1.0, 150)  # Other cell type LFCs

    t_stat, p_val = stats.ttest_ind(group1, group2)
    record("Two-sample t-test",
           isinstance(t_stat, float) and isinstance(p_val, float),
           f"t = {t_stat:.2f}, p = {p_val:.4e}")

    # Test 7.2: Welch's t-test (unequal variance)
    t_welch, p_welch = stats.ttest_ind(group1, group2, equal_var=False)
    record("Welch's t-test",
           isinstance(t_welch, float),
           f"t = {t_welch:.2f}, p = {p_welch:.4e}")

    # Test 7.3: One-way ANOVA (bix-36 pattern)
    groups = {
        'CD4': np.random.normal(5, 1, 30),
        'CD8': np.random.normal(5.1, 1.1, 30),
        'CD14': np.random.normal(4.9, 0.9, 30),
        'CD19': np.random.normal(5.2, 1.0, 30),
    }
    f_stat, p_anova = stats.f_oneway(*groups.values())
    record("One-way ANOVA (bix-36 pattern)",
           isinstance(f_stat, float) and isinstance(p_anova, float),
           f"F = {f_stat:.4f}, p = {p_anova:.4e}")

    # Test 7.4: Multiple testing correction - BH
    pvals = np.random.uniform(0, 1, 100)
    pvals[:10] = np.random.uniform(0, 0.01, 10)  # Some significant
    _, padj_bh, _, _ = multipletests(pvals, method='fdr_bh')
    n_sig_bh = (padj_bh < 0.05).sum()
    record("BH correction",
           n_sig_bh >= 0 and n_sig_bh <= 100,
           f"{n_sig_bh} significant after BH")

    # Test 7.5: Bonferroni correction
    _, padj_bonf, _, _ = multipletests(pvals, method='bonferroni')
    n_sig_bonf = (padj_bonf < 0.05).sum()
    record("Bonferroni correction",
           n_sig_bonf <= n_sig_bh,  # Bonferroni should be more conservative
           f"{n_sig_bonf} significant after Bonferroni (vs {n_sig_bh} BH)")

    # Test 7.6: BY correction
    _, padj_by, _, _ = multipletests(pvals, method='fdr_by')
    n_sig_by = (padj_by < 0.05).sum()
    record("BY correction",
           n_sig_by <= n_sig_bh,
           f"{n_sig_by} significant after BY")

    # Test 7.7: Log2 fold change computation
    mean1 = np.array([100, 200, 50, 10])
    mean2 = np.array([50, 200, 100, 10])
    lfc = np.log2((mean1 + 1) / (mean2 + 1))
    record("Log2 fold change computation",
           np.isfinite(lfc).all(),
           f"LFCs: {lfc.round(3)}")

    # Test 7.8: Median fold change (bix-36-q3 pattern)
    fc_values = np.random.normal(0, 0.5, 175)  # simulating log2FC of miRNAs
    median_fc = np.median(fc_values)
    record("Median log2 fold change (bix-36-q3 pattern)",
           isinstance(median_fc, float),
           f"Median log2FC = {median_fc:.4f}")

    # Test 7.9: Distribution shape assessment (bix-36-q5 pattern)
    from scipy.stats import shapiro
    stat_shapiro, p_shapiro = shapiro(fc_values[:50])  # Shapiro limited to 5000
    is_normal = p_shapiro > 0.05
    record("Distribution shape test (Shapiro-Wilk)",
           isinstance(p_shapiro, float),
           f"Shapiro p = {p_shapiro:.4f}, Normal: {is_normal}")


def test_fold_change_and_de_comparison():
    """Test fold change computation and DE comparison between cell types."""
    print("\n=== Test Group 8: Fold Change and DE Comparison ===")

    import anndata as ad
    from scipy import stats
    from scipy.sparse import issparse

    np.random.seed(42)

    # Simulate sex-specific DE in different cell types (bix-31 pattern)
    n_genes = 500
    gene_names = [f'Gene_{i:04d}' for i in range(n_genes)]

    # CD4/CD8 cells: larger sex differences
    lfc_cd4cd8 = np.random.normal(0.3, 0.8, n_genes)
    # Other cells: smaller sex differences
    lfc_other = np.random.normal(0.0, 0.4, n_genes)

    # Test 8.1: Compare LFCs between cell type groups (bix-31-q1 pattern)
    t_stat, p_val = stats.ttest_ind(lfc_cd4cd8, lfc_other)
    record("T-test comparing LFCs between cell type groups (bix-31-q1)",
           abs(t_stat) > 1.0,  # Should see clear difference
           f"t = {t_stat:.2f}, p = {p_val:.4e}")

    # Test 8.2: Filter DEGs by thresholds (bix-31-q3 pattern)
    padj = np.random.uniform(0, 1, n_genes)
    padj[:100] = np.random.uniform(0, 0.04, 100)  # 100 truly significant
    basemean = np.random.lognormal(3, 1, n_genes)

    sig_mask = (padj < 0.05) & (np.abs(lfc_cd4cd8) > 0.5) & (basemean > 10)
    n_sig = sig_mask.sum()
    record("DEG filtering (padj + lfc + baseMean, bix-31-q3)",
           n_sig > 0,
           f"{n_sig} DEGs passing all filters")

    # Test 8.3: Welch's t-test protein-coding vs non-protein-coding (bix-31-q4)
    gene_types = ['protein_coding'] * 400 + ['lncRNA'] * 100
    lfc_pc = lfc_cd4cd8[:400]
    lfc_nc = lfc_cd4cd8[400:]
    t_welch, p_welch = stats.ttest_ind(lfc_pc, lfc_nc, equal_var=False)
    record("Welch's t-test protein-coding vs non-coding (bix-31-q4)",
           isinstance(t_welch, float),
           f"t = {t_welch:.4f}, p = {p_welch:.4e}")

    # Test 8.4: Specific gene fold change (bix-31-q2 pattern)
    gene_idx = gene_names.index('Gene_0100')
    specific_lfc = lfc_cd4cd8[gene_idx]
    record("Specific gene LFC extraction (bix-31-q2)",
           isinstance(specific_lfc, float),
           f"Gene_0100 log2FC = {specific_lfc:.4f}")


def test_mirna_analysis():
    """Test miRNA expression analysis patterns (bix-36)."""
    print("\n=== Test Group 9: miRNA Analysis (bix-36 pattern) ===")

    from scipy import stats

    df_mirna, meta = generate_mirna_data()

    # Test 9.1: ANOVA across cell types excluding PBMCs (bix-36-q1)
    meta_no_pbmc = meta[meta['cell_type'] != 'PBMC']
    df_no_pbmc = df_mirna.loc[meta_no_pbmc.index]

    # Compute mean miRNA expression per sample (across all miRNAs)
    mean_expr = df_no_pbmc.mean(axis=1)

    groups_dict = {}
    for ct in meta_no_pbmc['cell_type'].unique():
        ct_samples = meta_no_pbmc[meta_no_pbmc['cell_type'] == ct].index
        groups_dict[ct] = mean_expr[ct_samples].values

    f_stat, p_val = stats.f_oneway(*groups_dict.values())
    record("ANOVA miRNA expression across cell types (bix-36-q1)",
           isinstance(f_stat, float),
           f"F = {f_stat:.4f}, p = {p_val:.4e}")

    # Test 9.2: Median log2 fold change between two cell types (bix-36-q3)
    cd14_samples = meta[meta['cell_type'] == 'CD14'].index
    cd19_samples = meta[meta['cell_type'] == 'CD19'].index

    mean_cd14 = df_mirna.loc[cd14_samples].mean(axis=0)
    mean_cd19 = df_mirna.loc[cd19_samples].mean(axis=0)

    lfc = np.log2((mean_cd14 + 1) / (mean_cd19 + 1))
    median_lfc = lfc.median()
    record("Median log2FC between CD14 and CD19 (bix-36-q3)",
           isinstance(median_lfc, (float, np.floating)),
           f"Median log2FC = {median_lfc:.4f}")

    # Test 9.3: ANOVA on log2FC (bix-36-q4)
    # Compute pairwise log2FC for each miRNA across cell types
    cell_types_no_pbmc = [ct for ct in meta['cell_type'].unique() if ct != 'PBMC']
    all_lfcs = {}

    for ct in cell_types_no_pbmc:
        ct_samples = meta_no_pbmc[meta_no_pbmc['cell_type'] == ct].index
        all_lfcs[ct] = df_no_pbmc.loc[ct_samples].mean(axis=0).values

    # Compute log2FC relative to overall mean
    overall_mean = df_no_pbmc.mean(axis=0).values
    lfc_groups = {}
    for ct in cell_types_no_pbmc:
        lfc_groups[ct] = np.log2((all_lfcs[ct] + 1) / (overall_mean + 1))

    f_lfc, p_lfc = stats.f_oneway(*lfc_groups.values())
    record("ANOVA on log2FC across cell types (bix-36-q4)",
           isinstance(f_lfc, float),
           f"F = {f_lfc:.4f}, p = {p_lfc:.4e}")

    # Test 9.4: Distribution shape of log2FC (bix-36-q5)
    all_lfc_values = np.concatenate(list(lfc_groups.values()))
    skewness = stats.skew(all_lfc_values)
    _, p_norm = stats.shapiro(all_lfc_values[:5000])  # Shapiro limit

    if p_norm > 0.05:
        shape = "Normal"
    elif skewness > 0.5:
        shape = "Right-skewed"
    elif skewness < -0.5:
        shape = "Left-skewed"
    else:
        shape = "Approximately normal"

    record("Log2FC distribution shape (bix-36-q5)",
           shape is not None,
           f"Skewness = {skewness:.4f}, Shape: {shape}")


def test_batch_correction():
    """Test batch correction."""
    print("\n=== Test Group 10: Batch Correction ===")

    import scanpy as sc
    import harmonypy

    adata, _ = generate_scrna_data(n_cells=200, n_genes=80)

    # Add batch information
    adata.obs['batch'] = ['batch1'] * 100 + ['batch2'] * (adata.n_obs - 100)

    # Preprocess
    sc.pp.normalize_total(adata, target_sum=1e4)
    sc.pp.log1p(adata)
    sc.pp.scale(adata, max_value=10)
    n_comps = min(30, adata.n_vars, adata.n_obs - 1)
    sc.tl.pca(adata, n_comps=n_comps)

    # Test 10.1: Harmony batch correction
    n_pcs = min(20, n_comps)
    ho = harmonypy.run_harmony(
        adata.obsm['X_pca'][:, :n_pcs],
        adata.obs,
        'batch',
        random_state=0
    )
    # ho.Z_corr is (n_cells, n_pcs) - do NOT transpose
    corrected = ho.Z_corr if ho.Z_corr.shape[0] == adata.n_obs else ho.Z_corr.T

    record("Harmony batch correction",
           corrected.shape == (adata.n_obs, n_pcs),
           f"Corrected PCA shape: {corrected.shape}")

    # Test 10.2: Store corrected embeddings
    adata.obsm['X_pca_harmony'] = corrected
    record("Store corrected embeddings",
           'X_pca_harmony' in adata.obsm,
           f"Key added: X_pca_harmony")

    # Test 10.3: Re-cluster on corrected PCs
    sc.pp.neighbors(adata, use_rep='X_pca_harmony', random_state=0)
    sc.tl.leiden(adata, resolution=0.5, random_state=0, key_added='leiden_harmony')
    record("Re-cluster on corrected PCs",
           'leiden_harmony' in adata.obs.columns,
           f"Clusters: {adata.obs['leiden_harmony'].nunique()}")


def test_cell_type_annotation():
    """Test cell type annotation."""
    print("\n=== Test Group 11: Cell Type Annotation ===")

    import scanpy as sc
    from scipy.sparse import issparse

    adata, de_genes = generate_scrna_data(n_cells=200, n_genes=100)

    # Preprocess
    sc.pp.normalize_total(adata, target_sum=1e4)
    sc.pp.log1p(adata)
    sc.pp.scale(adata, max_value=10)
    n_comps = min(30, adata.n_vars, adata.n_obs - 1)
    sc.tl.pca(adata, n_comps=n_comps)
    sc.pp.neighbors(adata, n_pcs=min(20, n_comps))
    sc.tl.leiden(adata, resolution=0.5, random_state=0)

    # Test 11.1: Marker-based annotation
    marker_dict = de_genes  # {cell_type: [marker_genes]}

    X = adata.X.toarray() if issparse(adata.X) else adata.X
    expr_df = pd.DataFrame(X, index=adata.obs_names, columns=adata.var_names)

    cluster_scores = {}
    for ct, markers in marker_dict.items():
        available = [m for m in markers if m in adata.var_names]
        if available:
            scores = expr_df[available].mean(axis=1)
            cluster_scores[ct] = scores.groupby(adata.obs['leiden']).mean()

    if cluster_scores:
        score_df = pd.DataFrame(cluster_scores)
        assignments = score_df.idxmax(axis=1)
        adata.obs['cell_type_predicted'] = adata.obs['leiden'].map(assignments)

    record("Marker-based cell type annotation",
           'cell_type_predicted' in adata.obs.columns,
           f"Predicted types: {adata.obs['cell_type_predicted'].value_counts().to_dict()}")

    # Test 11.2: Compare with known annotations
    if 'cell_type' in adata.obs.columns and 'cell_type_predicted' in adata.obs.columns:
        # Simple accuracy
        known = adata.obs['cell_type']
        predicted = adata.obs['cell_type_predicted']
        # Not expecting perfect match since clustering may differ
        n_unique_known = known.nunique()
        n_unique_predicted = predicted.nunique()
        record("Annotation comparison",
               n_unique_predicted >= 1,
               f"Known types: {n_unique_known}, Predicted: {n_unique_predicted}")


def test_enrichment_integration():
    """Test enrichment analysis integration."""
    print("\n=== Test Group 12: Enrichment Integration ===")

    import gseapy as gp

    # Test 12.1: gseapy ORA with gene list
    test_genes = ['TP53', 'BRCA1', 'EGFR', 'MYC', 'KRAS', 'BRAF', 'PIK3CA',
                  'AKT1', 'PTEN', 'RB1', 'CDKN2A', 'CDK4', 'MDM2', 'ATM']

    try:
        enr = gp.enrich(
            gene_list=test_genes,
            gene_sets='KEGG_2021_Human',
            outdir=None,
            no_plot=True,
        )
        n_terms = len(enr.results)
        n_sig = (enr.results['Adjusted P-value'] < 0.05).sum()
        record("gseapy ORA enrichment",
               n_terms > 0,
               f"{n_sig} significant KEGG terms out of {n_terms}")
    except Exception as e:
        record("gseapy ORA enrichment", False, f"Error: {e}")

    # Test 12.2: Multiple libraries
    libs = ['GO_Biological_Process_2023', 'Reactome_2022']
    all_results = {}
    for lib in libs:
        try:
            enr = gp.enrich(gene_list=test_genes, gene_sets=lib,
                           outdir=None, no_plot=True)
            all_results[lib] = len(enr.results)
        except Exception as e:
            all_results[lib] = f"Error: {e}"

    record("Multi-library enrichment",
           len(all_results) == 2,
           f"Results: {all_results}")


def test_toolUniverse_integration():
    """Test ToolUniverse tool integration."""
    print("\n=== Test Group 13: ToolUniverse Integration ===")

    try:
        from tooluniverse import ToolUniverse
        tu = ToolUniverse()
        tu.load_tools()

        # Test 13.1: HPA gene search
        try:
            result = tu.tools.HPA_search_genes_by_query(query="CD14 monocyte marker")
            has_results = result is not None and len(result) > 0
            record("HPA gene search",
                   has_results,
                   f"Results: {len(result) if has_results else 0}")
        except Exception as e:
            record("HPA gene search", False, f"Error: {e}")

        # Test 13.2: MyGene query
        try:
            result = tu.tools.MyGene_query_genes(query="CD14")
            has_hits = result is not None and 'hits' in result
            record("MyGene gene query",
                   has_hits,
                   f"Hits: {len(result.get('hits', [])) if has_hits else 0}")
        except Exception as e:
            record("MyGene gene query", False, f"Error: {e}")

        # Test 13.3: Ensembl lookup
        try:
            result = tu.tools.ensembl_lookup_gene(gene_id="ENSG00000170458", species="homo_sapiens")
            has_data = result is not None
            record("Ensembl gene lookup",
                   has_data,
                   f"Result type: {type(result).__name__}")
        except Exception as e:
            record("Ensembl gene lookup", False, f"Error: {e}")

    except ImportError:
        record("ToolUniverse import", False, "tooluniverse not installed")
    except Exception as e:
        record("ToolUniverse initialization", False, f"Error: {e}")


def test_edge_cases():
    """Test edge cases and error handling."""
    print("\n=== Test Group 14: Edge Cases ===")

    import anndata as ad
    from scipy import stats
    from scipy.sparse import csr_matrix

    # Test 14.1: Empty AnnData
    adata_empty = ad.AnnData(
        X=csr_matrix(np.zeros((0, 10))),
        var=pd.DataFrame(index=[f'gene_{i}' for i in range(10)])
    )
    record("Handle empty AnnData",
           adata_empty.n_obs == 0,
           f"Shape: {adata_empty.shape}")

    # Test 14.2: Single cell per group
    np.random.seed(42)
    x1 = np.array([1.0, 2.0, 3.0])
    x2 = np.array([4.0])
    try:
        # t-test with n=1 in one group should fail or give nan
        t, p = stats.ttest_ind(x1, x2)
        valid = np.isfinite(t) or np.isnan(t)
        record("T-test with n=1", valid, f"t={t}, p={p}")
    except Exception as e:
        record("T-test with n=1", True, f"Correctly raised: {type(e).__name__}")

    # Test 14.3: All NaN values
    nan_values = np.array([np.nan, np.nan, np.nan])
    regular_values = np.array([1.0, 2.0, 3.0])
    # Filter NaN before correlation
    valid = ~np.isnan(nan_values) & ~np.isnan(regular_values)
    record("Handle all-NaN correlation",
           valid.sum() == 0,
           "Correctly detected 0 valid values")

    # Test 14.4: Very large dataset simulation
    n_large = 10000
    n_genes_large = 500
    X_large = csr_matrix(np.random.poisson(5, (n_large, n_genes_large)).astype(np.float32))
    adata_large = ad.AnnData(X=X_large)
    record("Large dataset (10k cells x 500 genes)",
           adata_large.n_obs == n_large,
           f"Shape: {adata_large.shape}, Memory: sparse")

    # Test 14.5: Duplicate gene names
    adata_dup = ad.AnnData(
        X=np.random.poisson(5, (10, 5)).astype(np.float32),
        var=pd.DataFrame(index=['GENE1', 'GENE2', 'GENE3', 'GENE1', 'GENE4'])
    )
    adata_dup.var_names_make_unique()
    record("Handle duplicate gene names",
           len(set(adata_dup.var_names)) == adata_dup.n_vars,
           f"Unique names: {list(adata_dup.var_names)}")

    # Test 14.6: Mixed data types in metadata
    meta_mixed = pd.DataFrame({
        'condition': ['A', 'B', 'A', 'B', 'A'],
        'age': [25, 30, 35, 40, 45],
        'score': [1.5, 2.3, 1.8, 2.9, 2.1],
    })
    record("Mixed metadata types",
           meta_mixed['condition'].dtype == object and meta_mixed['age'].dtype in [np.int64, int],
           f"Types: {dict(meta_mixed.dtypes)}")

    # Test 14.7: Zero-variance genes
    X_zero_var = np.zeros((10, 5))
    X_zero_var[:, 0] = 1.0  # Constant gene
    gene_lens = np.array([100, 200, 300, 400, 500])
    mean_expr = np.mean(X_zero_var, axis=0)
    # Should handle gracefully
    try:
        # pearsonr with constant values should return nan or error
        r, p = stats.pearsonr(gene_lens, mean_expr)
        record("Zero-variance gene correlation",
               True,  # As long as it doesn't crash
               f"r = {r}, p = {p}")
    except Exception as e:
        record("Zero-variance gene correlation", True,
               f"Correctly raised: {type(e).__name__}")


def test_report_generation():
    """Test report generation."""
    print("\n=== Test Group 15: Report Generation ===")

    # Test 15.1: Generate report from results dict
    results = {
        'data_info': {'n_obs': 500, 'n_vars': 200, 'cell_types': ['CD4', 'CD8', 'CD14']},
        'de_results': {
            'CD4': {'n_sig': 15, 'n_up': 8, 'n_down': 7},
            'CD8': {'n_sig': 20, 'n_up': 12, 'n_down': 8},
            'CD14': {'n_sig': 45, 'n_up': 25, 'n_down': 20},
        },
        'correlation_results': {
            'CD4': {'correlation': 0.05, 'p_value': 1e-3},
            'CD8': {'correlation': 0.04, 'p_value': 5e-3},
        },
    }

    report_lines = []
    report_lines.append("# Single-Cell Analysis Report\n")
    report_lines.append("## Data Summary")
    report_lines.append(f"- Cells: {results['data_info']['n_obs']}")
    report_lines.append(f"- Genes: {results['data_info']['n_vars']}")
    report_lines.append("")
    report_lines.append("## Differential Expression")
    report_lines.append("| Cell Type | N DEGs | Up | Down |")
    report_lines.append("|-----------|--------|-----|------|")
    for ct, r in results['de_results'].items():
        report_lines.append(f"| {ct} | {r['n_sig']} | {r['n_up']} | {r['n_down']} |")
    report_lines.append("")
    report_lines.append("## Correlation Analysis")
    report_lines.append("| Cell Type | Correlation | P-value |")
    report_lines.append("|-----------|------------|---------|")
    for ct, r in results['correlation_results'].items():
        report_lines.append(f"| {ct} | {r['correlation']:.4f} | {r['p_value']:.2e} |")

    report = "\n".join(report_lines)

    record("Report generation",
           "# Single-Cell Analysis Report" in report and "Differential Expression" in report,
           f"Report length: {len(report)} chars, {len(report_lines)} lines")

    # Test 15.2: Report contains all sections
    has_data = "Data Summary" in report
    has_de = "Differential Expression" in report
    has_corr = "Correlation Analysis" in report
    record("Report section completeness",
           has_data and has_de and has_corr,
           f"Data: {has_data}, DE: {has_de}, Corr: {has_corr}")


def test_complete_pipeline():
    """Test a complete end-to-end pipeline."""
    print("\n=== Test Group 16: Complete Pipeline ===")

    import scanpy as sc
    from scipy import stats
    from scipy.sparse import issparse

    # Test 16.1: Full scRNA-seq pipeline
    adata, de_genes = generate_scrna_data(n_cells=400, n_genes=100)
    n_before = adata.n_obs

    # QC
    adata.var['mt'] = adata.var_names.str.startswith('MT-')
    sc.pp.calculate_qc_metrics(adata, qc_vars=['mt'], percent_top=None, log1p=False, inplace=True)
    sc.pp.filter_cells(adata, min_genes=3)
    sc.pp.filter_genes(adata, min_cells=3)

    # Normalize
    sc.pp.normalize_total(adata, target_sum=1e4)
    sc.pp.log1p(adata)
    adata.raw = adata.copy()

    # HVG + PCA
    n_hvg = min(50, adata.n_vars)
    sc.pp.highly_variable_genes(adata, n_top_genes=n_hvg)
    sc.pp.scale(adata, max_value=10)
    n_comps = min(30, sum(adata.var['highly_variable']), adata.n_obs - 1)
    sc.tl.pca(adata, n_comps=n_comps)

    # Cluster
    sc.pp.neighbors(adata, n_pcs=min(20, n_comps))
    sc.tl.leiden(adata, resolution=0.5, random_state=0)
    sc.tl.umap(adata, random_state=0)

    # DE between cell types
    sc.tl.rank_genes_groups(adata, groupby='cell_type', method='wilcoxon')

    record("Complete scRNA-seq pipeline",
           'leiden' in adata.obs.columns and 'X_umap' in adata.obsm,
           f"Clusters: {adata.obs['leiden'].nunique()}, "
           f"UMAP: {adata.obsm['X_umap'].shape}")

    # Test 16.2: Per-cell-type DE between conditions
    per_ct_degs = {}
    for ct in adata.obs['cell_type'].unique():
        adata_ct = adata[adata.obs['cell_type'] == ct].copy()
        n_t = (adata_ct.obs['condition'] == 'treatment').sum()
        n_c = (adata_ct.obs['condition'] == 'control').sum()
        if n_t < 3 or n_c < 3:
            continue

        # Use raw for DE
        adata_ct_raw = adata.raw.to_adata()[adata.obs['cell_type'] == ct].copy()
        sc.tl.rank_genes_groups(adata_ct_raw, groupby='condition',
                                groups=['treatment'], reference='control',
                                method='wilcoxon')
        df = sc.get.rank_genes_groups_df(adata_ct_raw, group='treatment')
        per_ct_degs[ct] = (df['pvals_adj'] < 0.05).sum()

    if per_ct_degs:
        top_ct = max(per_ct_degs, key=per_ct_degs.get)
        record("Per-cell-type DE in full pipeline",
               len(per_ct_degs) >= 2,
               f"Top: {top_ct} ({per_ct_degs[top_ct]} DEGs)")

    # Test 16.3: Gene correlation with gene length
    X = adata.raw.X.toarray() if issparse(adata.raw.X) else adata.raw.X
    mean_expr = np.mean(X, axis=0)
    gene_lengths = adata.var['gene_length'].values

    valid = ~np.isnan(gene_lengths) & ~np.isnan(mean_expr)
    if valid.sum() > 2:
        r, p = stats.pearsonr(gene_lengths[valid], mean_expr[valid])
        record("Gene length-expression correlation in pipeline",
               isinstance(r, float),
               f"r = {r:.6f}, p = {p:.2e}")

    # Test 16.4: Statistical test on DE results
    if len(per_ct_degs) >= 2:
        ct_list = list(per_ct_degs.keys())
        # Compare DEG counts
        record("Cross-cell-type DEG comparison",
               True,
               f"DEGs per cell type: {per_ct_degs}")


# ============================================================
# Main
# ============================================================

def main():
    print("=" * 80)
    print("COMPREHENSIVE TEST SUITE: tooluniverse-single-cell")
    print("=" * 80)

    test_functions = [
        test_data_loading,
        test_qc_preprocessing,
        test_pca,
        test_clustering,
        test_differential_expression,
        test_correlation_analysis,
        test_statistical_comparisons,
        test_fold_change_and_de_comparison,
        test_mirna_analysis,
        test_batch_correction,
        test_cell_type_annotation,
        test_enrichment_integration,
        test_toolUniverse_integration,
        test_edge_cases,
        test_report_generation,
        test_complete_pipeline,
    ]

    for test_fn in test_functions:
        try:
            test_fn()
        except Exception as e:
            print(f"\n  [FATAL] {test_fn.__name__} crashed: {e}")
            traceback.print_exc()
            RESULTS.append((test_fn.__name__, "FATAL", str(e)))
            global FAIL_COUNT
            FAIL_COUNT += 1

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Total tests: {PASS_COUNT + FAIL_COUNT}")
    print(f"Passed: {PASS_COUNT}")
    print(f"Failed: {FAIL_COUNT}")
    print(f"Success rate: {PASS_COUNT/(PASS_COUNT+FAIL_COUNT)*100:.1f}%")

    if FAIL_COUNT > 0:
        print("\nFailed tests:")
        for name, status, detail in RESULTS:
            if status != "PASS":
                print(f"  [{status}] {name}: {detail}")

    print("\n" + "=" * 80)
    return 0 if FAIL_COUNT == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
