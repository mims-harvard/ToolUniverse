#!/usr/bin/env python3
"""Fit a binary OR ordinal logistic regression and emit odds ratios with 95% CIs.

Two main goals:

1. **Always report odds ratios** (`exp(coef)`) plus CIs and p-values for every
   coefficient — agents that solve regression questions often forget the
   exponentiation and report raw coefficients instead.

2. **Handle interaction terms automatically**. Pass `--interaction A:B` and
   the script will materialize a numeric `A * B` column, name it `A_B`,
   and add it to the model. You can pass multiple `--interaction` flags.

Output (TSV, plus a SCALARS block for the requested coef):

    NAME            ODDS_RATIO   CI_LOWER   CI_UPPER   COEF      P_VALUE
    TRTGRP_cat      1.6331       1.123      2.374      0.4905    1.082e-02
    expect_interact 0.7432       0.557      0.991      ...       ...
    ...

If `--coef-name <NAME>` is given, also print:

    REQUESTED_COEF        TRTGRP_cat
    REQUESTED_OR          1.6331
    REQUESTED_OR_LOWER    1.123
    REQUESTED_OR_UPPER    2.374
    REQUESTED_P_VALUE     1.082e-02

Workspace isolation
-------------------
This script does NOT write any output files. It only reads --csv (and
--meta if given) and prints to stdout — safe to run with any input
directory layout.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.miscmodels.ordinal_model import OrderedModel


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--csv", required=True, help="primary data CSV (read-only)")
    p.add_argument("--meta", default=None,
                   help="optional metadata CSV; merged on --merge-on")
    p.add_argument("--merge-on", default=None,
                   help="key column for --meta merge (e.g. USUBJID)")
    p.add_argument("--outcome", required=True,
                   help="outcome/response column name")
    p.add_argument("--outcome-type", choices=["binary", "ordinal"], default="ordinal",
                   help="binary -> sm.Logit, ordinal -> OrderedModel (default ordinal)")
    p.add_argument("--outcome-order", default=None,
                   help="comma-separated list defining ordinal ordering "
                        "(e.g. 'MILD,MODERATE,SEVERE'). If omitted, "
                        "natural sort of unique values is used.")
    p.add_argument("--predictors", required=True,
                   help="comma-separated list of predictor column names")
    p.add_argument("--encode", default=None,
                   help="comma-separated list of columns to label-encode "
                        "(e.g. 'expect_interact,patients_seen,TRTGRP')")
    p.add_argument("--encode-map", action="append", default=[],
                   help="explicit map for one column; e.g. "
                        "--encode-map 'TRTGRP:Placebo=0,BCG=1'. Repeatable.")
    p.add_argument("--interaction", action="append", default=[],
                   help="add interaction column 'A_B = A * B' for each "
                        "--interaction A:B. The new column name is added "
                        "to predictors automatically. Repeatable.")
    p.add_argument("--dropna", action="store_true",
                   help="drop rows with missing values in outcome or any predictor")
    p.add_argument("--coef-name", default=None,
                   help="if set, also print SCALARS block for this coefficient")
    p.add_argument("--ordinal-method", default="bfgs",
                   help="optimizer for OrderedModel.fit (default bfgs)")
    return p.parse_args()


def load_and_merge(csv: Path, meta: Path | None, merge_on: str | None) -> pd.DataFrame:
    df = pd.read_csv(csv)
    if meta is not None:
        if merge_on is None:
            sys.stderr.write("--meta requires --merge-on\n")
            sys.exit(2)
        meta_df = pd.read_csv(meta)
        df = df.merge(meta_df, on=merge_on, how="inner")
    return df


def parse_encode_map(spec: str) -> tuple[str, dict[str, int]]:
    """'TRTGRP:Placebo=0,BCG=1' -> ('TRTGRP', {'Placebo': 0, 'BCG': 1})."""
    col, mapping = spec.split(":", 1)
    pairs = [p.split("=") for p in mapping.split(",")]
    return col.strip(), {k.strip(): int(v.strip()) for k, v in pairs}


def encode_columns(df: pd.DataFrame, encode_cols: list[str], explicit_maps: dict[str, dict[str, int]]) -> pd.DataFrame:
    """Label-encode each requested column, using explicit map if provided."""
    for col in encode_cols:
        if col in explicit_maps:
            df[col + "_cat"] = df[col].map(explicit_maps[col])
            if df[col + "_cat"].isna().any():
                sys.stderr.write(
                    f"# warning: --encode-map for {col} produced NaN for some rows; "
                    f"unmapped values: {df.loc[df[col + '_cat'].isna(), col].unique().tolist()}\n"
                )
        else:
            categories = sorted(df[col].dropna().unique().tolist())
            mapping = {v: i for i, v in enumerate(categories)}
            df[col + "_cat"] = df[col].map(mapping)
            sys.stderr.write(f"# auto-encoded {col} -> {col}_cat using {mapping}\n")
    return df


def rewrite_encoded_predictors(predictors: list[str], encode_cols: list[str]) -> list[str]:
    """If a predictor was just encoded, swap its name for the _cat version."""
    out = []
    for p in predictors:
        if p in encode_cols:
            out.append(p + "_cat")
        else:
            out.append(p)
    return out


def add_interactions(df: pd.DataFrame, predictors: list[str], spec: list[str]) -> tuple[pd.DataFrame, list[str]]:
    """For each 'A:B' spec, create A_B = A * B and append A_B to predictors."""
    for s in spec:
        if ":" not in s:
            sys.stderr.write(f"--interaction must be 'A:B', got {s!r}\n")
            sys.exit(2)
        a, b = s.split(":", 1)
        a, b = a.strip(), b.strip()
        if a not in df.columns or b not in df.columns:
            sys.stderr.write(f"--interaction columns missing: {a}, {b} not in {list(df.columns)}\n")
            sys.exit(2)
        new_name = f"{a}_{b}"
        df[new_name] = df[a].astype(float) * df[b].astype(float)
        if new_name not in predictors:
            predictors.append(new_name)
        sys.stderr.write(f"# added interaction column {new_name} = {a} * {b}\n")
    return df, predictors


def build_outcome(df: pd.DataFrame, col: str, kind: str, order: str | None) -> pd.Series:
    if kind == "binary":
        y = df[col]
        levels = sorted(y.dropna().unique().tolist())
        if len(levels) != 2:
            sys.stderr.write(f"--outcome-type=binary but {col!r} has {len(levels)} levels: {levels}\n")
            sys.exit(2)
        if not all(isinstance(v, (int, np.integer)) for v in levels):
            mapping = {levels[0]: 0, levels[1]: 1}
            sys.stderr.write(f"# binary outcome {col} mapped {mapping}\n")
            y = y.map(mapping)
        return y.astype(int)

    # ordinal
    if order:
        cats_raw = [s.strip() for s in order.split(",")]
        # Match column dtype: if column is numeric, coerce category strings to int/float
        col_dtype = df[col].dtype
        if pd.api.types.is_integer_dtype(col_dtype):
            cats = [int(c) for c in cats_raw]
        elif pd.api.types.is_float_dtype(col_dtype):
            cats = [float(c) for c in cats_raw]
        else:
            cats = cats_raw
    else:
        cats = sorted(df[col].dropna().unique().tolist())
    cat = pd.Categorical(df[col], categories=cats, ordered=True)
    codes = cat.codes
    if (codes == -1).any():
        sys.stderr.write(
            f"# warning: outcome contains values outside --outcome-order: "
            f"{df[col][codes == -1].unique().tolist()}\n"
        )
    return pd.Series(codes, index=df.index, name=col)


def fit_binary(y: pd.Series, X: pd.DataFrame):
    Xc = sm.add_constant(X.astype(float))
    model = sm.Logit(y.astype(int), Xc)
    return model.fit(disp=0)


def fit_ordinal(y: pd.Series, X: pd.DataFrame, method: str):
    model = OrderedModel(y.astype(int), X.astype(float), distr="logit")
    return model.fit(method=method, disp=0)


def emit_table(result, predictors: list[str]) -> dict[str, dict[str, float]]:
    params = result.params
    pvals = result.pvalues
    ci = result.conf_int()
    ci.columns = [0, 1]

    rows = {}
    for name in params.index:
        coef = float(params[name])
        lo = float(ci.loc[name, 0])
        hi = float(ci.loc[name, 1])
        rows[name] = {
            "ODDS_RATIO": float(np.exp(coef)),
            "CI_LOWER":  float(np.exp(lo)),
            "CI_UPPER":  float(np.exp(hi)),
            "COEF":      coef,
            "P_VALUE":   float(pvals[name]),
        }

    print("=== ODDS RATIOS (exp(coef)) ===")
    print("NAME\tODDS_RATIO\tCI_LOWER\tCI_UPPER\tCOEF\tP_VALUE")
    for name, r in rows.items():
        print(f"{name}\t{r['ODDS_RATIO']:.6g}\t{r['CI_LOWER']:.6g}\t"
              f"{r['CI_UPPER']:.6g}\t{r['COEF']:.6g}\t{r['P_VALUE']:.6g}")
    return rows


def main() -> int:
    args = parse_args()
    csv_path = Path(args.csv).resolve()
    if not csv_path.exists():
        sys.stderr.write(f"CSV not found: {csv_path}\n")
        return 2

    df = load_and_merge(csv_path,
                        Path(args.meta).resolve() if args.meta else None,
                        args.merge_on)

    explicit_maps: dict[str, dict[str, int]] = {}
    for spec in args.encode_map:
        col, m = parse_encode_map(spec)
        explicit_maps[col] = m

    encode_cols = [c.strip() for c in args.encode.split(",")] if args.encode else []
    df = encode_columns(df, encode_cols, explicit_maps)

    predictors = [p.strip() for p in args.predictors.split(",")]
    predictors = rewrite_encoded_predictors(predictors, encode_cols)
    df, predictors = add_interactions(df, predictors, args.interaction)

    missing = [p for p in predictors if p not in df.columns]
    if missing:
        sys.stderr.write(
            f"predictors not in dataframe: {missing}\n"
            f"available columns: {list(df.columns)}\n"
        )
        return 2

    if args.dropna:
        before = len(df)
        df = df.dropna(subset=[args.outcome] + predictors)
        sys.stderr.write(f"# dropna kept {len(df)}/{before} rows\n")

    y = build_outcome(df, args.outcome, args.outcome_type, args.outcome_order)
    X = df[predictors].copy()

    print(f"=== MODEL ===")
    print(f"family: {args.outcome_type}")
    print(f"outcome: {args.outcome}  (n_levels = {y.nunique()}, n_obs = {len(y)})")
    print(f"predictors: {predictors}")
    print()

    if args.outcome_type == "binary":
        result = fit_binary(y, X)
    else:
        result = fit_ordinal(y, X, args.ordinal_method)

    rows = emit_table(result, predictors)

    if args.coef_name:
        if args.coef_name not in rows:
            sys.stderr.write(
                f"--coef-name {args.coef_name!r} not in fitted parameters: "
                f"{list(rows.keys())}\n"
            )
            return 2
        r = rows[args.coef_name]
        print()
        print("=== REQUESTED ===")
        print(f"REQUESTED_COEF\t{args.coef_name}")
        print(f"REQUESTED_OR\t{r['ODDS_RATIO']:.6g}")
        print(f"REQUESTED_OR_LOWER\t{r['CI_LOWER']:.6g}")
        print(f"REQUESTED_OR_UPPER\t{r['CI_UPPER']:.6g}")
        print(f"REQUESTED_COEF_VALUE\t{r['COEF']:.6g}")
        print(f"REQUESTED_P_VALUE\t{r['P_VALUE']:.6g}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
