"""Clinical trial adverse-event severity statistical test tool.

Wraps the skill script at
``skills/tooluniverse-statistical-modeling/scripts/prepare_ae_cohort.py``
so the merge-and-test logic is callable as a ToolUniverse tool.

Merge convention (matches bix-10 correct answer): take max(AESEV) per subject
across ALL AE records (no AEPT filtering), inner-join to DM on USUBJID.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any, Dict

from .base_tool import BaseTool
from .tool_registry import register_tool


# Resolve the skill script path and load it as a module so we don't duplicate
# logic. The skill script stays in place for direct Python use.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = (
    _REPO_ROOT
    / "skills"
    / "tooluniverse-statistical-modeling"
    / "scripts"
    / "prepare_ae_cohort.py"
)


def _load_script_module():
    """Dynamically import the skill script as a module."""
    if not _SCRIPT_PATH.exists():
        return None
    spec = importlib.util.spec_from_file_location(
        "_ae_cohort_script", str(_SCRIPT_PATH)
    )
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    # Avoid re-running argparse/main when importing
    saved_argv = sys.argv
    sys.argv = [str(_SCRIPT_PATH)]
    try:
        spec.loader.exec_module(module)
    finally:
        sys.argv = saved_argv
    return module


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

        module = _load_script_module()
        if module is None:
            return {
                "status": "error",
                "error": f"Skill script not available at {_SCRIPT_PATH}",
            }

        try:
            df = module.prepare_cohort(dm_file, ae_file, subgroup)
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
                chi2, p, dof, ct_dict = module.run_chi_square(df, group_col)
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
            result = module.run_ordinal(df, group_col, covariates)
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
