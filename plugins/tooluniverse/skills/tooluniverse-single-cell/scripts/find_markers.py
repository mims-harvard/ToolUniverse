#!/usr/bin/env python3
"""
Marker Gene Identification and Cell Type Annotation

Find marker genes for clusters and annotate cell types.
"""

import scanpy as sc
import pandas as pd
import numpy as np
from scipy.sparse import issparse


def find_marker_genes(adata, groupby='leiden', method='wilcoxon', n_genes=100):
    """Find marker genes for each group.

    Args:
        adata: AnnData (normalized, log-transformed)
        groupby: Column to group by
        method: 'wilcoxon', 't-test', or 'logreg'
        n_genes: Number of top genes per group

    Returns:
        adata with results in .uns['rank_genes_groups']
    """
    sc.tl.rank_genes_groups(
        adata,
        groupby=groupby,
        method=method,
        n_genes=n_genes,
        corr_method='benjamini-hochberg'
    )

    print(f"Found marker genes for {len(adata.obs[groupby].unique())} groups")
    return adata


def get_top_markers(adata, group, n_genes=10):
    """Get top marker genes for a specific group.

    Args:
        adata: AnnData with marker gene results
        group: Group name/ID
        n_genes: Number of top genes

    Returns:
        DataFrame with marker genes
    """
    markers = sc.get.rank_genes_groups_df(adata, group=str(group))
    return markers.head(n_genes)


def annotate_by_markers(adata, marker_dict, cluster_col='leiden', new_col='cell_type'):
    """Annotate clusters using known marker genes.

    Args:
        adata: AnnData with expression data
        marker_dict: {cell_type: [marker_genes]}
        cluster_col: Column with cluster labels
        new_col: Column to store cell type annotations

    Returns:
        adata with cell type annotations
    """
    X = adata.X.toarray() if issparse(adata.X) else adata.X
    expr_df = pd.DataFrame(X, index=adata.obs_names, columns=adata.var_names)

    # Score each cluster for each cell type
    cluster_scores = {}
    for ct, markers in marker_dict.items():
        available_markers = [m for m in markers if m in adata.var_names]
        if available_markers:
            scores = expr_df[available_markers].mean(axis=1)
            cluster_scores[ct] = scores.groupby(adata.obs[cluster_col]).mean()
        else:
            print(f"Warning: No markers found for {ct}")

    if cluster_scores:
        # Assign cell types
        score_df = pd.DataFrame(cluster_scores)
        assignments = score_df.idxmax(axis=1)
        adata.obs[new_col] = adata.obs[cluster_col].map(assignments)
        print(f"Annotated {len(assignments)} clusters")
    else:
        print("No annotations possible: no valid markers")

    return adata


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python find_markers.py <h5ad_file>")
        sys.exit(1)

    # Load data
    adata = sc.read_h5ad(sys.argv[1])

    # Find markers
    adata = find_marker_genes(adata, groupby='leiden', method='wilcoxon')

    # Print top markers for each cluster
    for cluster in adata.obs['leiden'].unique():
        print(f"\nCluster {cluster} top markers:")
        markers = get_top_markers(adata, cluster, n_genes=5)
        print(markers[['names', 'scores', 'pvals_adj']].to_string(index=False))

    # Example annotation (customize marker_dict)
    marker_dict = {
        'T cells': ['CD3D', 'CD3E'],
        'B cells': ['CD19', 'MS4A1'],
        'Monocytes': ['CD14', 'LYZ'],
        'NK cells': ['NKG7', 'GNLY'],
    }

    adata = annotate_by_markers(adata, marker_dict)

    # Save
    output_file = sys.argv[1].replace('.h5ad', '_with_markers.h5ad')
    adata.write_h5ad(output_file)
    print(f"\nSaved to: {output_file}")
