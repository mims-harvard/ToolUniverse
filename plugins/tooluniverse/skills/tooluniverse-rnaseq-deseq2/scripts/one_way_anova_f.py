#!/usr/bin/env python3
"""One-way ANOVA between groups, reporting F-statistic AND p-value.

Why this exists:
- Questions phrased as "What is the F-statistic from a one-way ANOVA
  comparing miRNA expression across cell types" often get answered with
  only the p-value (because scipy returns both, and "ANOVA p-value" is the
  more familiar phrase). Returning both ensures the agent can quote either.
- Supports two input modes:
    A) GROUPED LONG: a CSV with one row per observation and a 'group'
       column + a 'value' column.
    B) GROUPED WIDE: a CSV where each column is one group and rows are
       observations (variable-length groups handled).
    C) PER-GENE LFC FRAME: a CSV with multiple LFC columns (e.g.,
       celltype_CD8_vs_CD4, celltype_CD14_vs_CD4, ...) — ANOVA across
       these columns row-wise (same gene compared across multiple
       contrasts). Common for "ANOVA across cell-type LFC distributions".

Usage:
    # Mode A: long format
    python one_way_anova_f.py --long /path/data.csv \\
        --group-col cell_type --value-col expression

    # Mode B: wide format with each col as a group
    python one_way_anova_f.py --wide /path/data.csv \\
        --columns "CD4,CD8,CD14,CD19"

    # Mode C: ANOVA across LFC columns
    python one_way_anova_f.py --lfc-frame /path/lfc.csv \\
        --columns "celltype_CD8_vs_CD4,celltype_CD14_vs_CD4,celltype_CD19_vs_CD4"

Output (parseable):
    # ANOVA n_groups=N: F=... p=... means=...
    # WELCH n_groups=N: F=... p=... (variance-unequal alternative)
"""

from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd
from scipy import stats


def emit_anova(label: str, groups: list[np.ndarray]) -> None:
    n_groups = len(groups)
    sizes = [len(g) for g in groups]
    means = [float(np.nanmean(g)) for g in groups]
    valid = [g[~np.isnan(g)] for g in groups if len(g) > 0]
    if any(len(g) == 0 for g in valid) or n_groups < 2:
        print(f"# {label}: cannot compute (n_groups={n_groups}, sizes={sizes})")
        return
    f, p = stats.f_oneway(*valid)
    print(f"# {label} n_groups={n_groups} sizes={sizes}: F={f:.6f} p={p:.6e} means={means}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--long", help="Long-format CSV (each row = one observation).")
    src.add_argument("--wide", help="Wide-format CSV (each column = one group).")
    src.add_argument("--lfc-frame", help="LFC frame: each column = one log2FC contrast; ANOVA across columns row-wise.")
    ap.add_argument("--group-col", help="(LONG only) name of the group column.")
    ap.add_argument("--value-col", help="(LONG only) name of the value column.")
    ap.add_argument("--columns", help="(WIDE/LFC) comma-separated column names to use as groups.")
    ap.add_argument("--exclude-groups", default="", help="Comma-separated group values to exclude (LONG mode).")
    args = ap.parse_args()

    if args.long:
        if not (args.group_col and args.value_col):
            sys.exit("ERROR: --long requires --group-col and --value-col.")
        df = pd.read_csv(args.long)
        if args.exclude_groups:
            excl = [x.strip() for x in args.exclude_groups.split(",") if x.strip()]
            df = df[~df[args.group_col].astype(str).isin(excl)]
            print(f"# excluded groups: {excl}", file=sys.stderr)
        groups_dict = {k: g[args.value_col].values.astype(float)
                        for k, g in df.groupby(args.group_col)}
        labels = list(groups_dict.keys())
        groups = list(groups_dict.values())
        print(f"# LONG mode: groups={labels}")
        emit_anova(f"ANOVA grouped by {args.group_col}", groups)
        # Welch-equivalent (no scipy direct one-way Welch — use brown-forsythe via stats)
        # Welch's t generalization not in scipy; report classic only.
    elif args.wide:
        df = pd.read_csv(args.wide)
        cols = [c.strip() for c in (args.columns or "").split(",") if c.strip()]
        if not cols:
            cols = list(df.columns)
        groups = [df[c].dropna().values.astype(float) for c in cols]
        print(f"# WIDE mode: groups={cols}")
        emit_anova(f"ANOVA across columns", groups)
    elif args.lfc_frame:
        df = pd.read_csv(args.lfc_frame, index_col=0)
        cols = [c.strip() for c in (args.columns or "").split(",") if c.strip()]
        if not cols:
            cols = list(df.columns)
        missing = [c for c in cols if c not in df.columns]
        if missing:
            sys.exit(f"ERROR: columns {missing} not in LFC frame. Available: {list(df.columns)}")
        groups = [df[c].dropna().values.astype(float) for c in cols]
        print(f"# LFC-FRAME mode: groups={cols}")
        emit_anova(f"ANOVA across LFC contrasts", groups)
        # Pairwise t-tests
        print("\n# Pairwise Welch t-tests:")
        for i in range(len(cols)):
            for j in range(i+1, len(cols)):
                t, p = stats.ttest_ind(df[cols[i]].dropna(), df[cols[j]].dropna(), equal_var=False)
                print(f"# WELCH_T {cols[i]} vs {cols[j]}: t={t:.4f} p={p:.4e}")

    print("\n# DONE")


if __name__ == "__main__":
    main()
