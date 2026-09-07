"""Clinical trial adverse-event severity statistical test tool.

Merge convention (matches bix-10 correct answer): take max(AESEV) per subject
across ALL AE records (no AEPT filtering), inner-join to DM on USUBJID.

The implementation is inlined below rather than loaded from
``skills/tooluniverse-statistical-modeling/scripts/prepare_ae_cohort.py`` at
runtime: that path is resolved relative to the repository root, so it does not
exist under site-packages and the tool failed for every install from PyPI.
"""

from __future__ import annotations

import os
from typing import Any, Dict

import pandas as pd

from .base_tool import BaseTool
from .tool_registry import register_tool


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
    ct_dict = {
        str(k): {str(k2): int(v2) for k2, v2 in row.items()}
        for k, row in ct.to_dict(orient="index").items()
    }
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
        # Not ``dtype == object``: pandas 3 gives string columns a dedicated
        # ``str`` dtype, so that check silently skips the encoding and
        # statsmodels then fails with "Pandas data cast to numpy dtype of object".
        if not pd.api.types.is_numeric_dtype(X[col]):
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
        # ``.iloc``: these are positions, and pandas 3 treats an integer key on
        # a labelled Series as a label, raising KeyError.
        coef = float(result.params.iloc[idx])
        or_val = float(np.exp(coef))
        p_val = float(result.pvalues.iloc[idx])
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


@register_tool("ClinicalTrialAESeverityTestTool")
class ClinicalTrialAESeverityTestTool(BaseTool):
    """Merge DM + AE and run chi-square or ordinal logistic regression on AESEV.

    Parameters
    ----------
    dm_file : str
        Path to demographics CSV (must have ``USUBJID`` and group column).
    ae_file : str
        Path to adverse-events CSV (must have ``USUBJID`` and ``AESEV``).
    test : str
        One of ``"chi-square"``, ``"ordinal"``, or ``"prepare"`` (merge only).
    group_col : str
        Group column in DM (default ``"TRTGRP"``).
    subgroup : str, optional
        Filter expression ``"col=value"`` (e.g. ``"expect_interact=Yes"``).
    covariates : str, optional
        Comma-separated covariate column names (ordinal only).
    """

    def __init__(self, tool_config: Dict[str, Any], **kwargs):
        super().__init__(tool_config)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        dm_file = arguments.get("dm_file", "")
        ae_file = arguments.get("ae_file", "")
        test = arguments.get("test", "prepare")
        group_col = arguments.get("group_col", "TRTGRP")
        subgroup = arguments.get("subgroup", "") or ""
        covariates_raw = arguments.get("covariates", "") or ""

        if not dm_file or not os.path.exists(dm_file):
            return {"status": "error", "error": f"DM file not found: {dm_file}"}
        if not ae_file or not os.path.exists(ae_file):
            return {"status": "error", "error": f"AE file not found: {ae_file}"}
        if test not in {"chi-square", "ordinal", "prepare"}:
            return {
                "status": "error",
                "error": f"Invalid test: {test}. Use chi-square, ordinal, or prepare.",
            }

        try:
            df = prepare_cohort(dm_file, ae_file, subgroup)
        except KeyError as exc:
            return {"status": "error", "error": f"Missing required column: {exc}"}
        except Exception as exc:  # noqa: BLE001
            return {"status": "error", "error": f"Cohort prep failed: {exc}"}

        if df is None or len(df) == 0:
            return {
                "status": "error",
                "error": "Cohort has zero subjects after merge/filter",
            }
        if group_col not in df.columns:
            return {
                "status": "error",
                "error": f"group_col '{group_col}' not in DM columns: {list(df.columns)[:20]}",
            }

        aesev_dist = {
            int(k): int(v)
            for k, v in df["AESEV"].value_counts().sort_index().to_dict().items()
        }
        base = {
            "n_subjects": int(len(df)),
            "group_col": group_col,
            "subgroup": subgroup,
            "aesev_distribution": aesev_dist,
        }

        if test == "prepare":
            return {"status": "success", "data": base}

        if test == "chi-square":
            try:
                chi2, p, dof, ct_dict = run_chi_square(df, group_col)
            except Exception as exc:  # noqa: BLE001
                return {"status": "error", "error": f"Chi-square failed: {exc}"}
            return {
                "status": "success",
                "data": {
                    **base,
                    "test": "chi-square",
                    "test_statistic": float(chi2),
                    "p_value": float(p),
                    "dof": int(dof),
                    "contingency_table": ct_dict,
                },
            }

        # ordinal
        covariates = [c.strip() for c in covariates_raw.split(",") if c.strip()]
        missing = [c for c in covariates if c not in df.columns]
        if missing:
            return {
                "status": "error",
                "error": f"Covariates not in DM columns: {missing}",
            }
        try:
            result = run_ordinal(df, group_col, covariates)
        except Exception as exc:  # noqa: BLE001
            return {"status": "error", "error": f"Ordinal regression failed: {exc}"}
        if result is None:
            return {
                "status": "error",
                "error": "statsmodels unavailable or ordinal fit failed",
            }

        primary = result["odds_ratios"].get(group_col, {})
        return {
            "status": "success",
            "data": {
                **base,
                "test": "ordinal",
                "covariates": covariates,
                "or": primary.get("or"),
                "ci_lower": primary.get("ci_lower"),
                "ci_upper": primary.get("ci_upper"),
                "p_value": primary.get("p_value"),
                "odds_ratios": result["odds_ratios"],
                "model_summary": result["model_summary"],
            },
        }
