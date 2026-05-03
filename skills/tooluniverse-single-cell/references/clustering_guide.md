# Clustering Methods for Single-Cell Data

Guide to different clustering methods: Leiden, Louvain, hierarchical, and bootstrap consensus clustering.

---

## Leiden Clustering (Recommended)

Best all-around method for single-cell data.

```python
import scanpy as sc

# Build neighbor graph
sc.pp.neighbors(adata, n_neighbors=15, n_pcs=30)

# Run Leiden
sc.tl.leiden(adata, resolution=0.5, random_state=0)

print(f"Clusters: {adata.obs['leiden'].nunique()}")
```

**Resolution parameter**:
- Higher = More clusters
- Typical range: 0.3 - 1.5
- Start with 0.5, adjust based on biology

---

## Louvain Clustering

Alternative to Leiden (older algorithm).

```python
sc.tl.louvain(adata, resolution=0.5, random_state=0)
```

**Leiden vs Louvain**:
- Leiden: Better optimization, guaranteed connected communities
- Louvain: Faster, may produce disconnected communities
- For publication: Use Leiden

---

## Hierarchical Clustering

For expression matrices (not single-cell level).

```python
from scipy.cluster.hierarchy import linkage, fcluster, dendrogram
from scipy.spatial.distance import pdist
import numpy as np

def hierarchical_clustering(expression_df, n_clusters=3, method='ward', metric='euclidean'):
    """Hierarchical clustering on expression matrix.

    Args:
        expression_df: DataFrame (samples as rows, genes as columns)
        n_clusters: Number of clusters
        method: 'ward', 'complete', 'average', 'single'
        metric: Distance metric

    Returns:
        dict with labels, linkage_matrix
    """
    # Compute linkage
    if method == 'ward':
        Z = linkage(expression_df.values, method='ward')
    else:
        dist = pdist(expression_df.values, metric=metric)
        Z = linkage(dist, method=method)

    # Cut tree
    labels = fcluster(Z, t=n_clusters, criterion='maxclust')

    # Cluster sizes
    unique, counts = np.unique(labels, return_counts=True)
    for c, n in zip(unique, counts):
        print(f"  Cluster {c}: {n} samples")

    return {
        'labels': labels,
        'linkage_matrix': Z,
        'n_clusters': n_clusters
    }

# Example
result = hierarchical_clustering(expr_df, n_clusters=3, method='ward')
```

**Linkage methods**:
- `ward`: Minimizes within-cluster variance (best for most data)
- `complete`: Maximum distance between clusters (compact clusters)
- `average`: Average distance (balanced)
- `single`: Minimum distance (can create chains)

---

## Bootstrap Consensus Clustering

Robust clustering with logistic regression prediction (BixBench pattern).

```python
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

def bootstrap_consensus_clustering(expression_df, n_clusters=3, n_iterations=50,
                                    train_fraction=0.7, random_state=42):
    """Bootstrap consensus clustering.

    Args:
        expression_df: DataFrame (samples as rows, genes as columns)
        n_clusters: Number of clusters
        n_iterations: Bootstrap iterations
        train_fraction: Fraction for training
        random_state: Random seed

    Returns:
        dict with labels, consensus_matrix, consistent_count
    """
    np.random.seed(random_state)
    n_samples = len(expression_df)
    n_train = int(n_samples * train_fraction)

    # Consensus matrices
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

        # Predict test labels
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

    # Normalize
    with np.errstate(divide='ignore', invalid='ignore'):
        train_consensus_norm = np.where(train_count > 0, train_consensus / train_count, 0)
        test_consensus_norm = np.where(test_count > 0, test_consensus / test_count, 0)

    # Final clustering
    combined_consensus = (train_consensus_norm + test_consensus_norm) / 2
    np.fill_diagonal(combined_consensus, 1.0)

    from scipy.spatial.distance import squareform
    dist = 1 - combined_consensus
    np.fill_diagonal(dist, 0)
    dist = np.maximum(dist, 0)
    dist = (dist + dist.T) / 2
    condensed = squareform(dist)
    Z_final = linkage(condensed, method='average')
    final_labels = fcluster(Z_final, t=n_clusters, criterion='maxclust')

    # Count consistent samples
    consistent_count = 0
    for s in range(n_samples):
        cluster = final_labels[s]
        same_cluster = np.where(final_labels == cluster)[0]
        same_cluster = same_cluster[same_cluster != s]

        if len(same_cluster) > 0:
            train_scores = [train_consensus_norm[s, j] for j in same_cluster if train_count[s, j] > 0]
            test_scores = [test_consensus_norm[s, j] for j in same_cluster if test_count[s, j] > 0]

            if train_scores and test_scores:
                if np.mean(train_scores) > 0.7 and np.mean(test_scores) > 0.7:
                    consistent_count += 1

    print(f"Consistently classified: {consistent_count}/{n_samples}")

    return {
        'labels': final_labels,
        'train_consensus': train_consensus_norm,
        'test_consensus': test_consensus_norm,
        'combined_consensus': combined_consensus,
        'consistent_count': consistent_count
    }

# Example
result = bootstrap_consensus_clustering(expr_df, n_clusters=3, n_iterations=50)
print(f"Answer: {result['consistent_count']} samples consistently classified")
```

---

## PCA for Clustering

Perform PCA on expression matrix for BixBench questions.

```python
from sklearn.decomposition import PCA
import pandas as pd
import numpy as np

def manual_pca(expression_df, log_transform='log10', pseudocount=1):
    """Run PCA with specific transforms.

    Args:
        expression_df: DataFrame (samples as rows, genes as columns)
        log_transform: 'log10', 'log2', 'log1p', or None
        pseudocount: Pseudocount for log

    Returns:
        dict with variance_ratio, pc_coords, loadings
    """
    X = expression_df.values.astype(float)

    # Transform
    if log_transform == 'log10':
        X = np.log10(X + pseudocount)
    elif log_transform == 'log2':
        X = np.log2(X + pseudocount)
    elif log_transform == 'log1p':
        X = np.log1p(X)

    # Run PCA
    n_components = min(X.shape[0], X.shape[1])
    pca = PCA(n_components=n_components)
    pc_coords = pca.fit_transform(X)

    # Results
    result = {
        'variance_ratio': pca.explained_variance_ratio_,
        'variance_explained': pca.explained_variance_,
        'pc_coords': pd.DataFrame(
            pc_coords,
            index=expression_df.index,
            columns=[f'PC{i+1}' for i in range(n_components)]
        ),
        'loadings': pd.DataFrame(
            pca.components_.T,
            index=expression_df.columns,
            columns=[f'PC{i+1}' for i in range(n_components)]
        ),
        'cumulative_variance': np.cumsum(pca.explained_variance_ratio_)
    }

    print(f"PC1: {result['variance_ratio'][0]*100:.2f}% variance")
    print(f"PC1-10: {result['cumulative_variance'][9]*100:.2f}% variance")

    return result

# Example
pca_result = manual_pca(expr_df, log_transform='log10', pseudocount=1)
```

---

## Choosing the Right Method

| Use Case | Method | When to Use |
|----------|--------|-------------|
| Single-cell clustering | **Leiden** | Default for scRNA-seq |
| Older pipeline compatibility | **Louvain** | If comparing to old analyses |
| Expression matrix clustering | **Hierarchical** | Bulk RNA-seq, <1000 samples |
| Robust clustering | **Bootstrap consensus** | Need confidence estimates |
| Dimensionality reduction | **PCA** | Variance analysis, visualization |

---

## Validation

### Silhouette Score
```python
from sklearn.metrics import silhouette_score

# After clustering
silhouette_avg = silhouette_score(X, labels)
print(f"Silhouette score: {silhouette_avg:.3f}")
# Range: -1 to 1. >0.5 is good.
```

### Cluster Stability
```python
# Run clustering multiple times with different random seeds
from collections import Counter

all_labels = []
for seed in range(10):
    sc.tl.leiden(adata, resolution=0.5, random_state=seed, key_added=f'leiden_{seed}')
    all_labels.append(adata.obs[f'leiden_{seed}'])

# Check consistency
# (Implementation depends on label alignment)
```

---

## See Also

- **scanpy_workflow.md** - Prepare data for clustering
- **marker_identification.md** - Annotate clusters after clustering
