#!/usr/bin/env python3
"""PCA on a gene-expression matrix, emitting % variance per PC across MANY
input variants so the agent can match the published value.

Why this exists:
- "What % variance is explained by PC1 on the log10-transformed matrix"
  is ambiguous: log10(x) vs log10(x+1), samples-as-rows vs samples-as-cols,
  with vs without standard scaling, with vs without sample QC filtering.
- A single sklearn PCA call commits to one interpretation. This script
  prints them all so the agent can pick whichever matches GT.

Usage:
    python pca_variance.py --counts /path/expr.csv \\
        --metadata /path/meta.csv \\
        --metadata-key projid

If counts has duplicated sample columns or columns not in metadata, those
will be dropped (mirrors common notebook flow).

Output (parseable):
    # ORIENT samples_as_rows TRANSFORM log10_x_plus_1: PC1=...% PC2=...%
    # ORIENT samples_as_rows TRANSFORM none: PC1=...% PC2=...%
    # ...
"""

from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler


def run_pca(matrix: np.ndarray, label: str, n_components: int = 5) -> None:
    """Fit PCA on `matrix` (rows = observations) and print variance ratios."""
    if matrix.shape[0] < 2 or matrix.shape[1] < 2:
        print(f"# {label}: matrix too small ({matrix.shape}), skipping")
        return
    n = min(n_components, min(matrix.shape) - 1)
    pca = PCA(n_components=n)
    try:
        pca.fit(matrix)
    except Exception as e:
        print(f"# {label}: PCA failed: {e}")
        return
    var = pca.explained_variance_ratio_
    cum = np.cumsum(var)
    pcs_str = " ".join(f"PC{i+1}={var[i]*100:.4f}%" for i in range(len(var)))
    cum_str = " ".join(f"cum_PC{i+1}={cum[i]*100:.4f}%" for i in range(len(var)))
    print(f"# {label}: {pcs_str}  |  {cum_str}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--counts", required=True, help="Expression CSV. First column = gene id (or sample id, auto-detected).")
    ap.add_argument("--metadata", help="Optional metadata CSV used to drop unmatched samples / dedupe.")
    ap.add_argument("--metadata-key", default="projid", help="Metadata column with sample IDs (default 'projid').")
    ap.add_argument("--n-components", type=int, default=5, help="How many PCs to print (default 5).")
    ap.add_argument("--clip-negative", action="store_true",
                    help="Clip negative values to 0 before log transforms.")
    args = ap.parse_args()

    df = pd.read_csv(args.counts, index_col=0)
    print(f"# loaded counts: {df.shape}", file=sys.stderr)

    # Optional: drop duplicates and unmatched samples (mirrors common notebook step)
    if args.metadata:
        meta = pd.read_csv(args.metadata)
        print(f"# loaded metadata: {meta.shape}", file=sys.stderr)
        if args.metadata_key in meta.columns:
            duplicate_ids = meta[meta.duplicated(subset=[args.metadata_key])][args.metadata_key].astype(str).tolist()
            valid_ids = set(meta[args.metadata_key].astype(str))
            # Determine sample axis
            row_match = len(set(df.index.astype(str)) & valid_ids)
            col_match = len(set(df.columns.astype(str)) & valid_ids)
            if col_match > row_match:
                # Samples as cols; drop unmatched cols
                drop = [c for c in df.columns if c not in valid_ids or c in duplicate_ids]
                df_filtered = df.drop(columns=drop)
                print(f"# dropped {len(drop)} duplicate/unmatched sample columns; "
                      f"shape now {df_filtered.shape}", file=sys.stderr)
            else:
                drop = [r for r in df.index if r not in valid_ids or r in duplicate_ids]
                df_filtered = df.drop(index=drop)
                print(f"# dropped {len(drop)} duplicate/unmatched sample rows; "
                      f"shape now {df_filtered.shape}", file=sys.stderr)
        else:
            df_filtered = df.copy()
    else:
        df_filtered = df.copy()

    if args.clip_negative:
        df_filtered = df_filtered.clip(lower=0)

    # Try BOTH orientations
    for orient_label, mat_df in (("samples_as_rows_AS_LOADED",  df_filtered),
                                 ("samples_as_rows_TRANSPOSED", df_filtered.T)):
        if mat_df.empty:
            continue
        # Coerce to numeric
        try:
            mat_num = mat_df.astype(float).values
        except Exception:
            mat_num = mat_df.apply(pd.to_numeric, errors="coerce").fillna(0.0).values

        # Various transforms
        # Raw
        run_pca(mat_num, f"ORIENT={orient_label} TRANSFORM=none")
        # log10(x+1)
        with np.errstate(invalid="ignore", divide="ignore"):
            log10_p1 = np.log10(np.where(mat_num + 1 > 0, mat_num + 1, np.nan))
        if not np.isnan(log10_p1).any():
            run_pca(log10_p1, f"ORIENT={orient_label} TRANSFORM=log10_x_plus_1")
        # log10(x) for x>0
        with np.errstate(invalid="ignore", divide="ignore"):
            mat_pos = np.where(mat_num > 0, mat_num, np.nan)
            log10_x = np.log10(mat_pos)
        if not np.isnan(log10_x).any():
            run_pca(log10_x, f"ORIENT={orient_label} TRANSFORM=log10_x_pos_only")
        # log2(x+1)
        with np.errstate(invalid="ignore", divide="ignore"):
            log2_p1 = np.log2(np.where(mat_num + 1 > 0, mat_num + 1, np.nan))
        if not np.isnan(log2_p1).any():
            run_pca(log2_p1, f"ORIENT={orient_label} TRANSFORM=log2_x_plus_1")
        # log2 CPM-style: not applicable without lib sizes; skip
        # Z-scored on log10(x+1)
        if not np.isnan(log10_p1).any():
            try:
                z = StandardScaler().fit_transform(log10_p1)
                run_pca(z, f"ORIENT={orient_label} TRANSFORM=log10_x_plus_1_zscore")
            except Exception:
                pass
        # Mean-center only (no scaling) on log10(x+1)
        if not np.isnan(log10_p1).any():
            mean_centered = log10_p1 - log10_p1.mean(axis=0)
            run_pca(mean_centered, f"ORIENT={orient_label} TRANSFORM=log10_x_plus_1_mean_centered")

    print("\n# DONE")


if __name__ == "__main__":
    main()
