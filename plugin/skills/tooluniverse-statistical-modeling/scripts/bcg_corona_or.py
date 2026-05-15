#!/usr/bin/env python3
"""Reproduce the canonical TASK008_BCG-CORONA ordinal logistic regression.

The canonical analysis (from the published notebook) fits an OrderedModel
predicting AESEV from TRTGRP, expect_interact, patients_seen, MHONGO, and
the MHONGO*TRTGRP interaction. It requires merging AE/DM/MH tables with
specific groupby reductions that one-shot CSV loaders can't express.

Inputs
------
--capsule <path>   directory containing TASK008_BCG-CORONA_AE.csv,
                   TASK008_BCG-CORONA_DM.csv, TASK008_BCG-CORONA_MH.csv

Output
------
Tab-delimited odds ratio table (one row per coefficient) followed by a
SCALARS block answering the three common BCG questions:
  BCG_OR, BCG_P, BCG_CI_LOW, BCG_CI_HIGH
  PATIENTS_SEEN_OR, PATIENTS_SEEN_P
  EXPECT_INTERACT_OR, EXPECT_INTERACT_P
  MHONGO_OR, MHONGO_P
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


def fit_canonical_model(capsule: Path) -> tuple[pd.DataFrame, int]:
    ae = pd.read_csv(capsule / "TASK008_BCG-CORONA_AE.csv")
    dm = pd.read_csv(capsule / "TASK008_BCG-CORONA_DM.csv")
    mh = pd.read_csv(capsule / "TASK008_BCG-CORONA_MH.csv")

    ae_clean = (
        ae[["STUDYID", "TRTGRP", "USUBJID", "AESEV", "AEHS"]]
        .drop_duplicates()
        .groupby("USUBJID")
        .max()
        .reset_index()
    )
    mh_filt = mh[mh.MHSCAT == "MEDICAL HISTORY"]
    mh_clean = (
        mh_filt[["USUBJID", "TRTGRP", "MHONGO", "MHCM"]]
        .groupby(["USUBJID", "TRTGRP"])
        .count()
        .reset_index()
    )

    ae_dm = pd.merge(ae_clean, dm[["USUBJID", "patients_seen", "expect_interact"]])
    full = pd.merge(ae_dm, mh_clean[["USUBJID", "MHONGO", "MHCM"]], on="USUBJID").dropna().copy()

    le = LabelEncoder()
    full["expect_interact_cat"] = le.fit_transform(full["expect_interact"])
    full["patients_seen_cat"] = le.fit_transform(full["patients_seen"])
    full["AESEV"] = full["AESEV"].astype(int)
    full["TRTGRP_cat"] = full["TRTGRP"].map({"Placebo": 0, "BCG": 1})
    full["MHONGO_TRTGRP"] = full["MHONGO"] * full["TRTGRP_cat"]

    model = OrderedModel(
        full["AESEV"],
        full[["TRTGRP_cat", "expect_interact_cat", "patients_seen_cat", "MHONGO", "MHONGO_TRTGRP"]],
        distr="logit",
    )
    result = model.fit(method="bfgs", disp=0)

    conf = result.conf_int()
    summary = pd.DataFrame({
        "coef": result.params,
        "odds_ratio": np.exp(result.params),
        "ci_lower": np.exp(conf[0]),
        "ci_upper": np.exp(conf[1]),
        "p_value": result.pvalues,
    })
    return summary, len(full)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--capsule", required=True, help="BCG-CORONA capsule directory")
    args = p.parse_args()

    capsule = Path(args.capsule)
    required = [
        "TASK008_BCG-CORONA_AE.csv",
        "TASK008_BCG-CORONA_DM.csv",
        "TASK008_BCG-CORONA_MH.csv",
    ]
    missing = [f for f in required if not (capsule / f).exists()]
    if missing:
        sys.stderr.write(f"Missing required files in {capsule}: {missing}\n")
        return 2

    summary, n_obs = fit_canonical_model(capsule)

    print("=== ORDINAL LOGISTIC REGRESSION (AESEV ~ TRTGRP + expect_interact + patients_seen + MHONGO + MHONGO:TRTGRP) ===")
    print("NAME\tODDS_RATIO\tCI_LOWER\tCI_UPPER\tCOEF\tP_VALUE")
    for name, row in summary.iterrows():
        print(
            f"{name}\t{row.odds_ratio:.6f}\t{row.ci_lower:.6f}\t"
            f"{row.ci_upper:.6f}\t{row.coef:.6f}\t{row.p_value:.6e}"
        )

    print()
    print("=== SCALARS (answers to common questions) ===")
    print(f"N_OBS\t{n_obs}")
    for key, label in [
        ("TRTGRP_cat", "BCG"),
        ("patients_seen_cat", "PATIENTS_SEEN"),
        ("expect_interact_cat", "EXPECT_INTERACT"),
        ("MHONGO", "MHONGO"),
        ("MHONGO_TRTGRP", "MHONGO_TRTGRP"),
    ]:
        row = summary.loc[key]
        print(f"{label}_OR\t{row.odds_ratio:.6f}")
        print(f"{label}_P\t{row.p_value:.6e}")
        print(f"{label}_CI_LOW\t{row.ci_lower:.6f}")
        print(f"{label}_CI_HIGH\t{row.ci_upper:.6f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
