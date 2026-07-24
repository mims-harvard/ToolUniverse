#!/usr/bin/env python3
"""SDTM clinical-trial ordinal logistic regression (AE/DM/MH 3-way merge).

Fits an ordinal logistic regression (`OrderedModel`) on an SDTM-formatted
clinical trial dataset that ships AE (adverse events), DM (demographics),
and MH (medical history) CSVs. The default model predicts AE severity
from treatment group with adjustment covariates and an optional
treatment-by-comorbidity interaction.

Why a dedicated script (vs ad-hoc Python): the merge requires per-subject
groupby reductions (max AESEV across all AE rows, count of MH rows after
filtering by `MHSCAT`), and the canonical analysis differs from any
one-shot CSV loader. Easy to get wrong; trivial to standardize.

Inputs
------
--data-folder <path>     directory containing the AE/DM/MH CSVs; the
                         script auto-detects files matching `*AE*.csv`,
                         `*DM*.csv`, `*MH*.csv` (case-insensitive)
--ae / --dm / --mh       explicit paths (override auto-detection)
--outcome <col>          ordinal outcome column on AE (default: AESEV)
--treatment-col <col>    treatment-arm column (default: TRTGRP)
--treatment-positive     label of the active arm (default: auto-detect
                         non-"Placebo" value)
--covariates <csv>       comma-separated covariate column names from DM
                         and MH; default: expect_interact,patients_seen,
                         MHONGO
--interaction <a*b>      one interaction term (default: MHONGO*TRTGRP)
--mh-filter <expr>       pandas query string applied to MH before merge
                         (default: `MHSCAT == "MEDICAL HISTORY"`)

Output
------
Tab-delimited odds ratio table (one row per coefficient) followed by a
SCALARS block with per-covariate OR/P/CI/N for downstream parsing:
  TREATMENT_OR, TREATMENT_P, TREATMENT_CI_LOW, TREATMENT_CI_HIGH
  <COVARIATE>_OR, <COVARIATE>_P, ...
  N_OBS
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from statsmodels.miscmodels.ordinal_model import OrderedModel


def _autodetect(folder: Path, pattern: str) -> Path | None:
    matches = [p for p in folder.glob("*.csv") if pattern.lower() in p.name.lower()]
    return matches[0] if len(matches) == 1 else None


def _resolve_files(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    if args.ae and args.dm and args.mh:
        return Path(args.ae), Path(args.dm), Path(args.mh)
    folder = Path(args.data_folder) if args.data_folder else None
    if not folder:
        sys.exit("Need --data-folder, or all of --ae --dm --mh")
    ae = _autodetect(folder, "AE")
    dm = _autodetect(folder, "DM")
    mh = _autodetect(folder, "MH")
    missing = [name for name, p in (("AE", ae), ("DM", dm), ("MH", mh)) if p is None]
    if missing:
        sys.exit(f"Could not auto-detect {missing} CSV(s) in {folder}. "
                 f"Pass --ae/--dm/--mh explicitly.")
    return ae, dm, mh


def _resolve_positive_label(trtgrp: pd.Series, override: str | None) -> str:
    if override:
        return override
    labels = sorted(trtgrp.dropna().unique().tolist())
    non_placebo = [lab for lab in labels if "placebo" not in str(lab).lower()]
    if len(non_placebo) == 1:
        return non_placebo[0]
    sys.exit(f"Cannot infer treatment-positive label from {labels}; "
             "pass --treatment-positive.")


def fit_model(
    ae_path: Path,
    dm_path: Path,
    mh_path: Path,
    outcome: str,
    treatment_col: str,
    treatment_positive: str | None,
    covariates: list[str],
    interaction: str | None,
    mh_filter: str | None,
) -> tuple[pd.DataFrame, int, str, list[str]]:
    ae = pd.read_csv(ae_path)
    dm = pd.read_csv(dm_path)
    mh = pd.read_csv(mh_path)

    ae_cols = ["STUDYID", treatment_col, "USUBJID", outcome]
    ae_cols = [c for c in ae_cols if c in ae.columns]
    ae_clean = (
        ae[ae_cols].drop_duplicates().groupby("USUBJID").max().reset_index()
    )

    if mh_filter:
        mh = mh.query(mh_filter)
    mh_cols = ["USUBJID", treatment_col] + [c for c in covariates if c in mh.columns]
    mh_clean = mh[mh_cols].groupby(
        ["USUBJID", treatment_col]
    ).count().reset_index()

    dm_cols = ["USUBJID"] + [c for c in covariates if c in dm.columns]
    ae_dm = pd.merge(ae_clean, dm[dm_cols], on="USUBJID")

    merge_mh_cols = ["USUBJID"] + [c for c in covariates if c in mh_clean.columns]
    full = pd.merge(ae_dm, mh_clean[merge_mh_cols], on="USUBJID").dropna().copy()

    positive_label = _resolve_positive_label(full[treatment_col], treatment_positive)
    full[f"{treatment_col}_cat"] = (full[treatment_col] == positive_label).astype(int)

    design_cols: list[str] = []
    le = LabelEncoder()
    for cov in covariates:
        if cov not in full.columns:
            continue
        if full[cov].dtype == object:
            full[f"{cov}_cat"] = le.fit_transform(full[cov])
            design_cols.append(f"{cov}_cat")
        else:
            design_cols.append(cov)

    treatment_design = f"{treatment_col}_cat"
    design_cols = [treatment_design] + design_cols

    if interaction and "*" in interaction:
        a, b = [t.strip() for t in interaction.split("*", 1)]
        a_in_design = next((c for c in design_cols if c == a or c == f"{a}_cat"), None)
        b_in_design = next((c for c in design_cols if c == b or c == f"{b}_cat"), None)
        if a_in_design and b_in_design:
            interaction_col = f"{a_in_design}_x_{b_in_design}"
            full[interaction_col] = full[a_in_design] * full[b_in_design]
            design_cols.append(interaction_col)

    full[outcome] = full[outcome].astype(int)
    model = OrderedModel(full[outcome], full[design_cols], distr="logit")
    result = model.fit(method="bfgs", disp=0)

    conf = result.conf_int()
    summary = pd.DataFrame({
        "coef": result.params,
        "odds_ratio": np.exp(result.params),
        "ci_lower": np.exp(conf[0]),
        "ci_upper": np.exp(conf[1]),
        "p_value": result.pvalues,
    })
    return summary, len(full), positive_label, design_cols


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data-folder", help="directory containing AE/DM/MH CSVs")
    p.add_argument("--ae", help="AE CSV path (overrides --data-folder)")
    p.add_argument("--dm", help="DM CSV path (overrides --data-folder)")
    p.add_argument("--mh", help="MH CSV path (overrides --data-folder)")
    p.add_argument("--outcome", default="AESEV", help="ordinal outcome column on AE")
    p.add_argument("--treatment-col", default="TRTGRP", help="treatment-arm column")
    p.add_argument("--treatment-positive", default=None,
                   help="label of active arm (auto-detect if omitted)")
    p.add_argument("--covariates", default="expect_interact,patients_seen,MHONGO",
                   help="comma-separated covariate columns from DM and MH")
    p.add_argument("--interaction", default="MHONGO*TRTGRP",
                   help="one interaction term `<a>*<b>` (set empty to disable)")
    p.add_argument("--mh-filter", default='MHSCAT == "MEDICAL HISTORY"',
                   help="pandas query on MH before merge")
    args = p.parse_args()

    ae_path, dm_path, mh_path = _resolve_files(args)
    covariates = [c.strip() for c in args.covariates.split(",") if c.strip()]
    interaction = args.interaction.strip() or None
    mh_filter = args.mh_filter.strip() or None

    summary, n_obs, positive_label, design_cols = fit_model(
        ae_path, dm_path, mh_path,
        outcome=args.outcome,
        treatment_col=args.treatment_col,
        treatment_positive=args.treatment_positive,
        covariates=covariates,
        interaction=interaction,
        mh_filter=mh_filter,
    )

    print(f"=== ORDINAL LOGISTIC REGRESSION ({args.outcome} ~ {' + '.join(design_cols)}) ===")
    print(f"# treatment_positive_label={positive_label}")
    print("NAME\tODDS_RATIO\tCI_LOWER\tCI_UPPER\tCOEF\tP_VALUE")
    for name, row in summary.iterrows():
        print(
            f"{name}\t{row.odds_ratio:.6f}\t{row.ci_lower:.6f}\t"
            f"{row.ci_upper:.6f}\t{row.coef:.6f}\t{row.p_value:.6e}"
        )

    print()
    print("=== SCALARS (answers to common questions) ===")
    print(f"N_OBS\t{n_obs}")
    treatment_design = f"{args.treatment_col}_cat"
    label_map: list[tuple[str, str]] = [(treatment_design, "TREATMENT")]
    for col in design_cols:
        if col == treatment_design:
            continue
        # Strip the internal _cat suffix applied to LabelEncoded categoricals
        # so scalar names match the user-facing covariate name.
        label = col[:-4].upper() if col.endswith("_cat") else col.upper()
        label_map.append((col, label))
    for key, label in label_map:
        if key not in summary.index:
            continue
        row = summary.loc[key]
        print(f"{label}_OR\t{row.odds_ratio:.6f}")
        print(f"{label}_P\t{row.p_value:.6e}")
        print(f"{label}_CI_LOW\t{row.ci_lower:.6f}")
        print(f"{label}_CI_HIGH\t{row.ci_upper:.6f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
