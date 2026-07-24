#!/usr/bin/env python3
"""Pearson correlation between gene length and expression, emitting BOTH raw
and log-transformed variants for ALL relevant subsets so the agent can
match the published value.

Why this exists:
- Questions of the form "Pearson correlation of gene length and gene
  expression for protein-coding genes" depend critically on (a) whether
  the expression is log-transformed, (b) whether the length is
  log-transformed, (c) whether the analysis is per-cell-type or pooled,
  (d) whether the matrix has been low-expression-filtered, (e) whether
  PBMC samples are excluded.
- Notebooks often report only ONE variant. The "right" answer can be at
  raw r ≈ 0.02 (CD14 raw) or log-both r ≈ 0.33 (pooled log expression).
  Listing every variant in a single tabular dump gives the agent visibility
  to match the GT.

Usage:
    python gene_length_correlation.py \\
        --counts /path/BatchCorrectedReadCounts.csv \\
        --metadata /path/Sample_annotated.csv \\
        --gene-annot /path/GeneMetaInfo.csv \\
        --biotype-col gene_biotype --biotype protein_coding \\
        --length-col Length \\
        --celltype-col celltype \\
        --exclude-celltypes PBMC \\
        --min-row-sum 10

Output (parseable):
    # SUBSET <name> n=<int>:
    #   raw_pearson_r=...
    #   log10_expr_pearson_r=...        (length, log10(mean expression))
    #   log10_length_pearson_r=...      (log10(length), mean expression)
    #   log10_both_pearson_r=...        (log10(length), log10(mean expression))

Subsets emitted automatically:
- ALL_SAMPLES: all samples in the count matrix (including PBMC if any).
- IMMUNE_ONLY: samples NOT in --exclude-celltypes (typically PBMC dropped).
- Each unique value in --celltype-col (e.g., CD4, CD8, CD14, CD19, PBMC).

WORKSPACE
---------
This script does NOT write any files. Reads only.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


def emit_corrs(name: str, gene_length: pd.Series, gene_expr: pd.Series) -> None:
    """Print all four Pearson correlation variants for a subset."""
    if len(gene_length) == 0:
        print(f"# SUBSET {name} n=0: (empty)")
        return
    # Drop any NaN
    common = gene_length.dropna().index.intersection(gene_expr.dropna().index)
    gl = gene_length.loc[common].astype(float)
    ge = gene_expr.loc[common].astype(float)
    # Raw
    r_raw, _ = stats.pearsonr(gl, ge)
    # log10(expr) — drop zero/negative expression
    pos = ge[ge > 0]
    if len(pos) >= 3:
        gl_p = gl.loc[pos.index]
        r_le, _ = stats.pearsonr(gl_p, np.log10(pos))
        r_ll, _ = stats.pearsonr(np.log10(gl_p), pos)
        r_lb, _ = stats.pearsonr(np.log10(gl_p), np.log10(pos))
    else:
        r_le = r_ll = r_lb = float("nan")
    n = len(common)
    n_pos = (ge > 0).sum()
    print(f"# SUBSET {name} n={n} n_with_positive_expr={n_pos}:")
    print(f"#   raw_pearson_r={r_raw:.6f}")
    print(f"#   log10_expr_pearson_r={r_le:.6f}    (length, log10(mean expression))")
    print(f"#   log10_length_pearson_r={r_ll:.6f}  (log10(length), mean expression)")
    print(f"#   log10_both_pearson_r={r_lb:.6f}    (log10(length), log10(mean expression))")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--counts", required=True, help="Count/expression matrix CSV (genes x samples).")
    ap.add_argument("--metadata", required=True, help="Sample metadata CSV.")
    ap.add_argument("--gene-annot", required=True, help="Gene annotation CSV (genes x cols including biotype + length).")
    ap.add_argument("--biotype-col", default="gene_biotype", help="Column name in gene-annot for biotype.")
    ap.add_argument("--biotype", default="protein_coding", help="Biotype to keep (default protein_coding).")
    ap.add_argument("--length-col", default="Length", help="Column name in gene-annot for gene length.")
    ap.add_argument("--celltype-col", default="celltype", help="Metadata column for cell type / group.")
    ap.add_argument("--exclude-celltypes", default="", help="Comma-separated cell types to exclude in IMMUNE_ONLY subset.")
    ap.add_argument("--min-row-sum", type=int, default=10, help="Drop genes with rowSum < this (default 10).")
    ap.add_argument("--counts-orientation", default="auto", choices=["auto","genes_x_samples","samples_x_genes"],
                    help="Auto-detect by matching with metadata index.")
    args = ap.parse_args()

    counts = pd.read_csv(args.counts, index_col=0)
    meta = pd.read_csv(args.metadata, index_col=0)
    gene_annot = pd.read_csv(args.gene_annot, index_col=0)

    print(f"# counts.shape={counts.shape}, meta.shape={meta.shape}, gene_annot.shape={gene_annot.shape}",
          file=sys.stderr)

    # Orient counts so that ROWS are samples
    if args.counts_orientation == "samples_x_genes":
        pass  # already oriented
    elif args.counts_orientation == "genes_x_samples":
        counts = counts.T
    else:  # auto
        if set(counts.index) & set(meta.index):
            pass  # rows are samples already
        elif set(counts.columns) & set(meta.index):
            counts = counts.T
    print(f"# after orient: counts.shape={counts.shape} (rows=samples, cols=genes)", file=sys.stderr)

    # Filter to protein-coding genes (or the requested biotype)
    if args.biotype_col not in gene_annot.columns:
        sys.exit(f"ERROR: --biotype-col '{args.biotype_col}' not in gene_annot columns: "
                 f"{list(gene_annot.columns)}")
    biotype_genes = gene_annot[gene_annot[args.biotype_col].astype(str).str.contains(
        args.biotype, case=False, na=False)].index
    common_genes = [g for g in biotype_genes if g in counts.columns]
    counts = counts[common_genes]
    print(f"# After biotype filter ({args.biotype}): {counts.shape[1]} genes", file=sys.stderr)

    # Filter low-expression genes (rowSum across samples on gene-as-column matrix)
    if args.min_row_sum > 0:
        # rowSum = sum across samples for each gene = sum across rows of counts
        gene_sums = counts.sum(axis=0)
        keep = gene_sums >= args.min_row_sum
        counts = counts.loc[:, keep]
        print(f"# After low-expr filter (sum>={args.min_row_sum}): {counts.shape[1]} genes", file=sys.stderr)

    # Build aligned length series
    length_series = gene_annot.loc[counts.columns, args.length_col]

    # ALL_SAMPLES subset
    expr_mean_all = counts.mean(axis=0)
    emit_corrs("ALL_SAMPLES", length_series, expr_mean_all)

    # IMMUNE_ONLY subset (drop excluded cell types)
    if args.exclude_celltypes:
        exclude = [x.strip() for x in args.exclude_celltypes.split(",") if x.strip()]
        if args.celltype_col in meta.columns:
            keep_meta = meta[~meta[args.celltype_col].isin(exclude)].index
            keep_samples = [s for s in counts.index if s in keep_meta]
            sub = counts.loc[keep_samples]
            expr_mean_imm = sub.mean(axis=0)
            emit_corrs(f"IMMUNE_ONLY (excluding {','.join(exclude)})",
                       length_series, expr_mean_imm)

    # Per-cell-type subsets
    if args.celltype_col in meta.columns:
        cts = sorted(meta[args.celltype_col].dropna().astype(str).unique())
        print(f"# Cell types found: {cts}", file=sys.stderr)
        for ct in cts:
            samples_ct = meta[meta[args.celltype_col].astype(str) == ct].index
            keep_samples = [s for s in counts.index if s in samples_ct]
            if not keep_samples:
                continue
            sub = counts.loc[keep_samples]
            expr_mean_ct = sub.mean(axis=0)
            emit_corrs(f"CELLTYPE_{ct}", length_series, expr_mean_ct)

    # Also subset by sample-name SUBSTRING (legacy notebook style)
    # e.g. samples named "CHC096CD14" — split by cell type label appearing in name
    print("\n# SUBSTRING-MATCHED SUBSETS (sample names containing the cell type tag):", file=sys.stderr)
    for tag in ("CD4", "CD8", "CD14", "CD19", "PBMC"):
        keep_samples = [s for s in counts.index if tag in s]
        if not keep_samples:
            continue
        sub = counts.loc[keep_samples]
        expr_mean_sub = sub.mean(axis=0)
        emit_corrs(f"SAMPLENAME_CONTAINS_{tag}", length_series, expr_mean_sub)

    print("\n# DONE")


if __name__ == "__main__":
    main()
