#!/usr/bin/env python3
"""Per-gene ANOVA and fold-change computation for expression data.

Computes F-statistics and median log2 fold changes at the GENE level
(not sample level). Each gene is one observation per group.

Usage:
    # ANOVA: F-stat comparing per-gene mean expression across groups
    python expression_anova.py --counts counts.csv --meta meta.csv \
        --group-col cell_type --exclude-groups PBMC \
        --mode anova

    # Fold change: per-gene log2FC between two groups, then median
    python expression_anova.py --counts counts.csv --meta meta.csv \
        --group-col cell_type --group-a CD14 --group-b CD19 \
        --mode fold_change
"""

import argparse
import sys

import numpy as np
import pandas as pd
from scipy import stats


def load_data(counts_path: str, meta_path: str, group_col: str, exclude_groups: list[str]):
    """Load count matrix and metadata, return per-gene group means."""
    counts = pd.read_csv(counts_path, index_col=0)
    meta = pd.read_csv(meta_path)

    # Try to match columns
    if meta.index.name is None and len(meta.columns) > 0:
        # Try first column as sample ID
        first_col = meta.columns[0]
        if set(meta[first_col].astype(str)).intersection(set(counts.columns)):
            meta = meta.set_index(first_col)

    # Align
    common = counts.columns.intersection(meta.index)
    if len(common) == 0:
        # Try transposing counts
        counts = counts.T
        common = counts.columns.intersection(meta.index)
    counts = counts[common]
    meta = meta.loc[common]

    # Filter groups
    groups = meta[group_col].unique()
    if exclude_groups:
        groups = [g for g in groups if g not in exclude_groups]
    meta = meta[meta[group_col].isin(groups)]
    counts = counts[meta.index]

    return counts, meta, group_col, groups


def per_gene_anova(counts, meta, group_col, groups):
    """Run one-way ANOVA comparing per-gene mean expression across groups.

    For each gene, compute its mean expression in each group.
    Then run f_oneway across the K groups of N gene-level means.
    """
    # Compute per-gene mean in each group
    group_means = {}
    for g in groups:
        samples = meta[meta[group_col] == g].index
        group_means[g] = counts[samples].mean(axis=1)

    # Each group has N values (one per gene)
    arrays = [group_means[g].values for g in groups]
    f_stat, p_val = stats.f_oneway(*arrays)

    print(f"Groups: {list(groups)}")
    print(f"Genes: {len(counts)}")
    print(f"F-statistic: {f_stat:.4f}")
    print(f"p-value: {p_val:.6f}")
    return f_stat, p_val


def per_gene_fold_change(counts, meta, group_col, group_a, group_b):
    """Compute per-gene log2 fold change between two groups, then median."""
    samples_a = meta[meta[group_col] == group_a].index
    samples_b = meta[meta[group_col] == group_b].index

    mean_a = counts[samples_a].mean(axis=1)
    mean_b = counts[samples_b].mean(axis=1)

    # Avoid log(0): add pseudocount
    pseudo = 1.0
    log2fc = np.log2((mean_a + pseudo) / (mean_b + pseudo))

    median_fc = np.median(log2fc)
    mean_fc = np.mean(log2fc)

    print(f"Group A ({group_a}): {len(samples_a)} samples")
    print(f"Group B ({group_b}): {len(samples_b)} samples")
    print(f"Genes: {len(log2fc)}")
    print(f"Median log2FC: {median_fc:.4f}")
    print(f"Mean log2FC: {mean_fc:.4f}")
    print(f"Genes with |log2FC| > 1: {(np.abs(log2fc) > 1).sum()}")
    return median_fc


def main():
    parser = argparse.ArgumentParser(description="Per-gene expression ANOVA/FC")
    parser.add_argument("--counts", required=True, help="Count matrix CSV (genes x samples)")
    parser.add_argument("--meta", required=True, help="Metadata CSV with group column")
    parser.add_argument("--group-col", required=True, help="Column name for groups")
    parser.add_argument("--exclude-groups", nargs="*", default=[], help="Groups to exclude")
    parser.add_argument("--mode", required=True, choices=["anova", "fold_change"])
    parser.add_argument("--group-a", default="", help="Group A for fold change")
    parser.add_argument("--group-b", default="", help="Group B for fold change")
    args = parser.parse_args()

    counts, meta, group_col, groups = load_data(
        args.counts, args.meta, args.group_col, args.exclude_groups
    )

    if args.mode == "anova":
        per_gene_anova(counts, meta, group_col, groups)
    elif args.mode == "fold_change":
        if not args.group_a or not args.group_b:
            print("--group-a and --group-b required for fold_change mode")
            sys.exit(1)
        per_gene_fold_change(counts, meta, group_col, args.group_a, args.group_b)


if __name__ == "__main__":
    main()
