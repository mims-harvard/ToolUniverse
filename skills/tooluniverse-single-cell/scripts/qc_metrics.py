#!/usr/bin/env python3
"""
QC Metrics Calculation for Single-Cell Data

Calculate QC metrics, apply filters, and generate QC reports.
"""

import scanpy as sc
import pandas as pd
import numpy as np
from scipy.sparse import issparse


def calculate_qc_metrics(adata, mt_pattern='MT-', return_stats=True):
    """Calculate comprehensive QC metrics.

    Args:
        adata: AnnData object
        mt_pattern: Pattern for mitochondrial genes (default: 'MT-')
        return_stats: Return statistics dict

    Returns:
        adata with QC metrics in .obs
        (optional) dict with QC statistics
    """
    # Identify mitochondrial genes
    adata.var['mt'] = adata.var_names.str.startswith(mt_pattern)

    # Calculate metrics
    sc.pp.calculate_qc_metrics(
        adata,
        qc_vars=['mt'],
        percent_top=None,
        log1p=False,
        inplace=True
    )

    stats = None
    if return_stats:
        stats = {
            'n_cells': adata.n_obs,
            'n_genes': adata.n_vars,
            'median_genes_per_cell': adata.obs['n_genes_by_counts'].median(),
            'median_counts_per_cell': adata.obs['total_counts'].median(),
            'median_pct_mt': adata.obs['pct_counts_mt'].median(),
        }
        print(f"Cells: {stats['n_cells']}")
        print(f"Genes: {stats['n_genes']}")
        print(f"Median genes/cell: {stats['median_genes_per_cell']:.0f}")
        print(f"Median counts/cell: {stats['median_counts_per_cell']:.0f}")
        print(f"Median %MT: {stats['median_pct_mt']:.1f}%")

    return (adata, stats) if return_stats else adata


def apply_qc_filters(adata, min_genes=200, max_genes=None, min_counts=None,
                     max_counts=None, max_pct_mt=20, min_cells=3):
    """Apply standard QC filters.

    Args:
        adata: AnnData with QC metrics
        min_genes: Minimum genes per cell
        max_genes: Maximum genes per cell (doublet filter)
        min_counts: Minimum UMI counts per cell
        max_counts: Maximum UMI counts per cell
        max_pct_mt: Maximum mitochondrial percentage
        min_cells: Minimum cells per gene

    Returns:
        Filtered AnnData
    """
    n_before = adata.n_obs

    # Filter cells
    sc.pp.filter_cells(adata, min_genes=min_genes)

    if min_counts is not None:
        sc.pp.filter_cells(adata, min_counts=min_counts)

    if max_counts is not None:
        adata = adata[adata.obs['total_counts'] < max_counts].copy()

    if max_genes is not None:
        adata = adata[adata.obs['n_genes_by_counts'] < max_genes].copy()

    if 'pct_counts_mt' in adata.obs.columns:
        adata = adata[adata.obs['pct_counts_mt'] < max_pct_mt].copy()

    # Filter genes
    sc.pp.filter_genes(adata, min_cells=min_cells)

    n_after = adata.n_obs
    print(f"QC filtering: {n_before} → {n_after} cells ({n_before - n_after} removed)")
    print(f"Genes after filtering: {adata.n_vars}")

    return adata


def detect_doublets(adata, expected_doublet_rate=0.06, threshold=0.25):
    """Detect doublets using scrublet.

    Args:
        adata: AnnData with raw counts
        expected_doublet_rate: Expected fraction of doublets
        threshold: Doublet score threshold

    Returns:
        adata with 'predicted_doublet' and 'doublet_score' in .obs
    """
    try:
        sc.external.pp.scrublet(adata, expected_doublet_rate=expected_doublet_rate)
        n_doublets = adata.obs['predicted_doublet'].sum()
        print(f"Detected {n_doublets} doublets ({n_doublets/adata.n_obs*100:.1f}%)")
    except Exception as e:
        print(f"Doublet detection failed: {e}")

    return adata


if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) < 2:
        print("Usage: python qc_metrics.py <h5ad_file>")
        sys.exit(1)

    # Load data
    adata = sc.read_h5ad(sys.argv[1])

    # Calculate QC metrics
    adata, stats = calculate_qc_metrics(adata, return_stats=True)

    # Apply filters
    adata = apply_qc_filters(
        adata,
        min_genes=200,
        max_pct_mt=20,
        min_cells=3
    )

    # Detect doublets (optional)
    # adata = detect_doublets(adata)

    # Save filtered data
    output_file = sys.argv[1].replace('.h5ad', '_qc_filtered.h5ad')
    adata.write_h5ad(output_file)
    print(f"Saved to: {output_file}")
