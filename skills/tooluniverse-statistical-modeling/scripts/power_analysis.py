#!/usr/bin/env python3
"""Two-sample power analysis: required N per group for a t-test.

Solves for the sample size that achieves a desired power for a two-sample
independent t-test, given an effect size measured from a pilot dataset.

Two ways to provide the effect size:

1. From a CSV: pass --csv, --value-col, --group-col, --group-a, --group-b.
   The script computes Cohen's d using the pooled standard deviation:

       sd_pooled = sqrt(((n1-1) * s1^2 + (n2-1) * s2^2) / (n1 + n2 - 2))
       d         = (mean_a - mean_b) / sd_pooled

2. Directly: pass --effect-size <float>.

Then solves for `N` per group with `statsmodels.stats.power.TTestIndPower`
at given --alpha (default 0.05) and --power (default 0.8) for a
--alternative ('two-sided' default; or 'larger' / 'smaller').

Output:

    GROUP_A_N        ...
    GROUP_A_MEAN     ...
    GROUP_B_N        ...
    GROUP_B_MEAN     ...
    POOLED_SD        ...
    COHENS_D         ...
    ALPHA            0.05
    POWER            0.8
    ALTERNATIVE      two-sided
    REQUIRED_N_PER_GROUP   337   (ceil of solve_power)
    REQUIRED_N_RAW         336.42

Workspace isolation
-------------------
This script reads --csv (read-only) and prints to stdout. It does not write
any files anywhere.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--csv", default=None, help="pilot data CSV; if omitted, --effect-size is required")
    p.add_argument("--value-col", default=None, help="numeric value column (response)")
    p.add_argument("--group-col", default=None, help="grouping column with two distinct levels")
    p.add_argument("--group-a", default=None, help="value of --group-col for group A (omit -> first sorted)")
    p.add_argument("--group-b", default=None, help="value of --group-col for group B (omit -> second sorted)")
    p.add_argument("--effect-size", type=float, default=None,
                   help="bypass --csv and pass Cohen's d directly")
    p.add_argument("--alpha", type=float, default=0.05)
    p.add_argument("--power", type=float, default=0.8)
    p.add_argument("--alternative", choices=["two-sided", "larger", "smaller"],
                   default="two-sided")
    p.add_argument("--ratio", type=float, default=1.0,
                   help="n2/n1 ratio (default 1.0 -> equal groups)")
    return p.parse_args()


def cohens_d_from_csv(args: argparse.Namespace) -> tuple[float, dict[str, float]]:
    if not all([args.csv, args.value_col, args.group_col]):
        sys.stderr.write("To compute Cohen's d, --csv, --value-col, --group-col are all required.\n")
        sys.exit(2)

    csv = Path(args.csv).resolve()
    if not csv.exists():
        sys.stderr.write(f"CSV not found: {csv}\n")
        sys.exit(2)

    df = pd.read_csv(csv)
    if args.value_col not in df.columns:
        sys.stderr.write(f"--value-col {args.value_col!r} not in {list(df.columns)}\n")
        sys.exit(2)
    if args.group_col not in df.columns:
        sys.stderr.write(f"--group-col {args.group_col!r} not in {list(df.columns)}\n")
        sys.exit(2)

    levels = df[args.group_col].dropna().unique().tolist()
    if len(levels) < 2:
        sys.stderr.write(f"--group-col {args.group_col!r} has only {levels} -> need 2 levels\n")
        sys.exit(2)

    if args.group_a is None and args.group_b is None:
        sorted_levels = sorted(levels, key=str)
        a, b = sorted_levels[0], sorted_levels[1]
    else:
        a = args.group_a if args.group_a is not None else [v for v in levels if str(v) != args.group_b][0]
        b = args.group_b if args.group_b is not None else [v for v in levels if str(v) != args.group_a][0]

    sa = df.loc[df[args.group_col].astype(str) == str(a), args.value_col].dropna().astype(float)
    sb = df.loc[df[args.group_col].astype(str) == str(b), args.value_col].dropna().astype(float)
    n1, n2 = len(sa), len(sb)
    if n1 < 2 or n2 < 2:
        sys.stderr.write(f"need >=2 samples per group; got {n1}, {n2}\n")
        sys.exit(2)

    var1 = sa.var(ddof=1)
    var2 = sb.var(ddof=1)
    sd_pooled = math.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
    if sd_pooled == 0:
        sys.stderr.write("pooled SD is zero — Cohen's d undefined\n")
        sys.exit(2)
    d = (sa.mean() - sb.mean()) / sd_pooled
    return d, {
        "GROUP_A": str(a),
        "GROUP_A_N": n1,
        "GROUP_A_MEAN": sa.mean(),
        "GROUP_A_SD": sa.std(ddof=1),
        "GROUP_B": str(b),
        "GROUP_B_N": n2,
        "GROUP_B_MEAN": sb.mean(),
        "GROUP_B_SD": sb.std(ddof=1),
        "POOLED_SD": sd_pooled,
    }


def main() -> int:
    args = parse_args()

    if args.effect_size is not None:
        d = float(args.effect_size)
        meta: dict[str, object] = {}
    else:
        d, meta = cohens_d_from_csv(args)

    try:
        from statsmodels.stats.power import TTestIndPower
    except ImportError as exc:
        sys.stderr.write(f"statsmodels required: {exc}\n")
        return 2

    analysis = TTestIndPower()
    n_raw = analysis.solve_power(
        effect_size=d,
        alpha=args.alpha,
        power=args.power,
        alternative=args.alternative,
        ratio=args.ratio,
    )
    n_required = int(math.ceil(n_raw))

    print("=== POWER ANALYSIS (TTestIndPower) ===")
    for k, v in meta.items():
        if isinstance(v, float):
            print(f"{k}\t{v:.6g}")
        else:
            print(f"{k}\t{v}")
    print(f"COHENS_D\t{d:.6g}")
    print(f"ALPHA\t{args.alpha}")
    print(f"POWER\t{args.power}")
    print(f"ALTERNATIVE\t{args.alternative}")
    print(f"RATIO_N2_OVER_N1\t{args.ratio}")
    print(f"REQUIRED_N_RAW\t{n_raw:.6g}")
    print(f"REQUIRED_N_PER_GROUP\t{n_required}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
