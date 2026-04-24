#!/usr/bin/env python3
"""Prepare clinical trial AE severity cohort for statistical analysis.

Merges demographics (DM) with adverse events (AE) using the correct
convention: max(AESEV) per subject across ALL AE records, inner join,
no pre-filtering by AEPT condition.

Usage:
    python prepare_ae_cohort.py --dm DM.csv --ae AE.csv
    python prepare_ae_cohort.py --dm DM.csv --ae AE.csv --subgroup "expect_interact=Yes"
    python prepare_ae_cohort.py --dm DM.csv --ae AE.csv --test chi-square --group TRTGRP
    python prepare_ae_cohort.py --dm DM.csv --ae AE.csv --test ordinal --group TRTGRP --covariates "patients_seen_cat,expect_interact_cat"
"""

import argparse
import sys

import pandas as pd


def prepare_cohort(dm_path: str, ae_path: str, subgroup: str = "") -> pd.DataFrame:
    """Prepare AE severity cohort with correct convention."""
    # Try latin1 encoding (common for clinical trial exports)
    for enc in ["utf-8", "latin1"]:
        try:
            dm = pd.read_csv(dm_path, encoding=enc)
            break
        except UnicodeDecodeError:
            continue

    for enc in ["utf-8", "latin1"]:
        try:
            ae = pd.read_csv(ae_path, encoding=enc)
            break
        except UnicodeDecodeError:
            continue

    # Max AESEV per subject across ALL AE records (no AEPT filtering)
    sev = ae.groupby("USUBJID")["AESEV"].max().reset_index()
    df = dm.merge(sev, on="USUBJID", how="inner").dropna(subset=["AESEV"])
    df["AESEV"] = df["AESEV"].astype(int)

    print(f"DM: {len(dm)} subjects")
    print(f"AE: {len(ae)} records, {ae['USUBJID'].nunique()} subjects")
    print(f"After merge (inner join, max AESEV): {len(df)} subjects")

    # Apply subgroup filter if specified
    if subgroup:
        col, val = subgroup.split("=")
        before = len(df)
        df = df[df[col.strip()] == val.strip()]
        print(f"After subgroup {subgroup}: {len(df)} subjects (from {before})")

    print(f"AESEV distribution: {df['AESEV'].value_counts().sort_index().to_dict()}")
    return df


def run_chi_square(df: pd.DataFrame, group_col: str):
    """Run chi-square test on group × AESEV. Returns (chi2, p, dof, ct_dict)."""
    from scipy import stats

    ct = pd.crosstab(df[group_col], df["AESEV"])
    print(f"\nContingency table ({group_col} × AESEV):")
    print(ct)
    chi2, p, dof, _ = stats.chi2_contingency(ct)
    print(f"\nChi-square = {chi2:.4f}, p = {p:.6f}, dof = {dof}")
    # ct_dict: nested dict keyed by group then AESEV level
    ct_dict = {str(k): {str(k2): int(v2) for k2, v2 in row.items()} for k, row in ct.to_dict(orient="index").items()}
    return float(chi2), float(p), int(dof), ct_dict


def run_ordinal(df: pd.DataFrame, group_col: str, covariates: list):
    """Run ordinal logistic regression. Returns dict with OR results and model summary."""
    try:
        from statsmodels.miscmodels.ordinal_model import OrderedModel
    except ImportError:
        print("statsmodels required: pip install statsmodels")
        return None

    import numpy as np

    formula_vars = [group_col] + covariates
    X = df[formula_vars].copy()

    # Convert categorical to numeric
    for col in X.columns:
        if X[col].dtype == object:
            X[col] = pd.Categorical(X[col]).codes

    model = OrderedModel(df["AESEV"], X, distr="logit")
    result = model.fit(method="bfgs", disp=False)
    print("\nOrdinal logistic regression:")
    print(result.summary())

    # Extract odds ratios (with 95% CI from conf_int)
    print("\nOdds ratios:")
    conf = result.conf_int()
    ors = {}
    for var in formula_vars:
        idx = list(X.columns).index(var)
        coef = float(result.params[idx])
        or_val = float(np.exp(coef))
        p_val = float(result.pvalues[idx])
        ci_low = float(np.exp(conf.iloc[idx, 0]))
        ci_high = float(np.exp(conf.iloc[idx, 1]))
        print(f"  {var}: OR = {or_val:.4f}, p = {p_val:.6f}")
        ors[var] = {
            "coef": coef,
            "or": or_val,
            "ci_lower": ci_low,
            "ci_upper": ci_high,
            "p_value": p_val,
        }
    return {
        "odds_ratios": ors,
        "model_summary": str(result.summary()),
        "primary_var": group_col,
    }


def main():
    parser = argparse.ArgumentParser(description="Prepare AE cohort")
    parser.add_argument("--dm", required=True, help="Demographics CSV")
    parser.add_argument("--ae", required=True, help="Adverse events CSV")
    parser.add_argument("--subgroup", default="", help="Subgroup filter (col=value)")
    parser.add_argument("--test", default="", choices=["", "chi-square", "ordinal"])
    parser.add_argument("--group", default="TRTGRP", help="Group variable")
    parser.add_argument("--covariates", default="", help="Comma-separated covariates")
    args = parser.parse_args()

    df = prepare_cohort(args.dm, args.ae, args.subgroup)

    if args.test == "chi-square":
        run_chi_square(df, args.group)
    elif args.test == "ordinal":
        covariates = [c.strip() for c in args.covariates.split(",") if c.strip()]
        run_ordinal(df, args.group, covariates)


if __name__ == "__main__":
    main()
