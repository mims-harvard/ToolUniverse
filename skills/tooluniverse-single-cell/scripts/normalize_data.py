#!/usr/bin/env python3
"""
Normalization Methods for Single-Cell Data

Standard normalization pipeline: library-size, log-transform, HVG, scale.
"""

import scanpy as sc
import numpy as np


def normalize_and_scale(adata, target_sum=1e4, log_transform=True,
                        n_top_genes=2000, scale=True, max_value=10,
                        store_raw=True):
    """Complete normalization pipeline.

    Args:
        adata: AnnData with raw counts
        target_sum: Target sum for library-size normalization
        log_transform: Whether to log1p transform
        n_top_genes: Number of highly variable genes (0 = skip)
        scale: Whether to z-score scale
        max_value: Maximum value after scaling (clip outliers)
        store_raw: Store raw counts in adata.raw

    Returns:
        Normalized AnnData
    """
    # Store raw counts
    if store_raw:
        adata.raw = adata.copy()
        print("Stored raw counts in adata.raw")

    # Library-size normalization
    sc.pp.normalize_total(adata, target_sum=target_sum)
    print(f"Normalized to {target_sum} counts per cell")

    # Log transform
    if log_transform:
        sc.pp.log1p(adata)
        print("Log1p transformed")

    # Highly variable genes
    if n_top_genes > 0:
        n_top_genes = min(n_top_genes, adata.n_vars)
        flavor = 'seurat_v3' if not log_transform else 'seurat'
        sc.pp.highly_variable_genes(adata, n_top_genes=n_top_genes, flavor=flavor)
        n_hvg = adata.var['highly_variable'].sum()
        print(f"Identified {n_hvg} highly variable genes")

    # Scale
    if scale:
        sc.pp.scale(adata, max_value=max_value)
        print(f"Scaled (max_value={max_value})")

    return adata


def normalize_only(adata, target_sum=1e4, log_transform=True):
    """Normalize without HVG selection or scaling.

    Use when you want to preserve all genes (e.g., for DE analysis).
    """
    adata.raw = adata.copy()
    sc.pp.normalize_total(adata, target_sum=target_sum)

    if log_transform:
        sc.pp.log1p(adata)

    return adata


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python normalize_data.py <h5ad_file>")
        sys.exit(1)

    # Load data
    adata = sc.read_h5ad(sys.argv[1])

    # Normalize
    adata = normalize_and_scale(
        adata,
        target_sum=1e4,
        log_transform=True,
        n_top_genes=2000,
        scale=True,
        max_value=10
    )

    # Save
    output_file = sys.argv[1].replace('.h5ad', '_normalized.h5ad')
    adata.write_h5ad(output_file)
    print(f"Saved to: {output_file}")
