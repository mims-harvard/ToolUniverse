"""Per-gene expression ANOVA / fold-change tool.

Wraps the skill script at
``skills/tooluniverse-statistical-modeling/scripts/expression_anova.py``.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

from .base_tool import BaseTool
from .tool_registry import register_tool


_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = (
    _REPO_ROOT
    / "skills"
    / "tooluniverse-statistical-modeling"
    / "scripts"
    / "expression_anova.py"
)


def _load_script_module():
    if not _SCRIPT_PATH.exists():
        return None
    spec = importlib.util.spec_from_file_location(
        "_expression_anova_script", str(_SCRIPT_PATH)
    )
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    saved_argv = sys.argv
    sys.argv = [str(_SCRIPT_PATH)]
    try:
        spec.loader.exec_module(module)
    finally:
        sys.argv = saved_argv
    return module


@register_tool("ExpressionANOVAPerGeneTool")
class ExpressionANOVAPerGeneTool(BaseTool):
    """Per-gene ANOVA / fold-change across groups.

    Each gene contributes one value per group (the mean expression of that
    gene across group samples). ``mode='anova'`` runs one-way ANOVA across
    the K groups of N gene-level means. ``mode='fold_change'`` computes
    per-gene log2FC between ``group_a`` and ``group_b`` (pseudocount=1),
    then returns the median across genes.
    """

    def __init__(self, tool_config: Dict[str, Any], **kwargs):
        super().__init__(tool_config)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        counts_file = arguments.get("counts_file", "")
        meta_file = arguments.get("meta_file", "")
        group_col = arguments.get("group_col", "")
        mode = arguments.get("mode", "anova")
        exclude_groups: List[str] = arguments.get("exclude_groups") or []
        group_a = arguments.get("group_a", "") or ""
        group_b = arguments.get("group_b", "") or ""

        if not counts_file or not os.path.exists(counts_file):
            return {"status": "error", "error": f"counts_file not found: {counts_file}"}
        if not meta_file or not os.path.exists(meta_file):
            return {"status": "error", "error": f"meta_file not found: {meta_file}"}
        if not group_col:
            return {"status": "error", "error": "group_col is required"}
        if mode not in {"anova", "fold_change"}:
            return {"status": "error", "error": f"Invalid mode: {mode}"}
        if mode == "fold_change" and (not group_a or not group_b):
            return {
                "status": "error",
                "error": "group_a and group_b required for mode='fold_change'",
            }

        module = _load_script_module()
        if module is None:
            return {
                "status": "error",
                "error": f"Skill script not available at {_SCRIPT_PATH}",
            }

        try:
            counts, meta, gcol, groups = module.load_data(
                counts_file, meta_file, group_col, list(exclude_groups)
            )
        except KeyError as exc:
            return {"status": "error", "error": f"Missing column: {exc}"}
        except Exception as exc:  # noqa: BLE001
            return {"status": "error", "error": f"Data load failed: {exc}"}

        if len(counts.columns) == 0:
            return {
                "status": "error",
                "error": "No overlapping samples between counts and metadata",
            }

        if mode == "anova":
            if len(groups) < 2:
                return {
                    "status": "error",
                    "error": f"ANOVA needs >=2 groups, got {list(groups)}",
                }
            try:
                result = module.per_gene_anova(counts, meta, gcol, groups)
            except Exception as exc:  # noqa: BLE001
                return {"status": "error", "error": f"ANOVA failed: {exc}"}
            return {"status": "success", "data": result}

        # fold_change — coerce group values to actual dtype of meta column
        group_vals = list(groups)
        str_map = {str(g): g for g in group_vals}
        resolved_a = str_map.get(str(group_a), group_a)
        resolved_b = str_map.get(str(group_b), group_b)
        if resolved_a not in group_vals or resolved_b not in group_vals:
            return {
                "status": "error",
                "error": f"group_a/group_b not found among groups {group_vals}",
            }
        try:
            result = module.per_gene_fold_change(
                counts, meta, gcol, resolved_a, resolved_b
            )
        except Exception as exc:  # noqa: BLE001
            return {"status": "error", "error": f"Fold-change failed: {exc}"}
        return {"status": "success", "data": result}
