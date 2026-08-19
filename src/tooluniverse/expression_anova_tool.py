"""Per-gene expression ANOVA / fold-change tool.

The implementation is inlined below rather than loaded from
``skills/tooluniverse-statistical-modeling/scripts/expression_anova.py`` at
runtime: that path is resolved relative to the repository root, so it does not
exist under site-packages and the tool failed for every install from PyPI.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from scipy import stats

from .base_tool import BaseTool
from .tool_registry import register_tool


def load_data(
    counts_path: str, meta_path: str, group_col: str, exclude_groups: list[str]
):
    """Load count matrix and metadata, return per-gene group means."""
    counts = pd.read_csv(counts_path, index_col=0)
    meta = pd.read_csv(meta_path)

    # Try to match columns: search each meta column for overlap with counts columns
    if meta.index.name is None and len(meta.columns) > 0:
        for col in meta.columns:
            if set(meta[col].astype(str)).intersection(set(counts.columns)):
                meta = meta.set_index(col)
                break
        else:
            # No meta column overlaps counts columns — try counts rows (after transpose)
            counts_t_cols = set(counts.index.astype(str))
            for col in meta.columns:
                if set(meta[col].astype(str)).intersection(counts_t_cols):
                    meta = meta.set_index(col)
                    break

    # Align
    common = counts.columns.intersection(meta.index)
    if len(common) == 0:
        # Try transposing counts
        counts = counts.T
        common = counts.columns.intersection(meta.index)
    counts = counts[common]
    meta = meta.loc[common]

    # Filter groups
    groups = meta[group_col].unique()
    if exclude_groups:
        groups = [g for g in groups if g not in exclude_groups]
    meta = meta[meta[group_col].isin(groups)]
    counts = counts[meta.index]

    return counts, meta, group_col, groups


def per_gene_anova(counts, meta, group_col, groups):
    """Run one-way ANOVA comparing per-gene mean expression across groups.

    For each gene, compute its mean expression in each group.
    Then run f_oneway across the K groups of N gene-level means.

    Returns dict: {f_statistic, p_value, n_genes, n_samples, groups}.
    """
    # Compute per-gene mean in each group
    group_means = {}
    for g in groups:
        samples = meta[meta[group_col] == g].index
        group_means[g] = counts[samples].mean(axis=1)

    # Each group has N values (one per gene)
    arrays = [group_means[g].values for g in groups]
    f_stat, p_val = stats.f_oneway(*arrays)

    print(f"Groups: {list(groups)}")
    print(f"Genes: {len(counts)}")
    print(f"F-statistic: {f_stat:.4f}")
    print(f"p-value: {p_val:.6f}")
    return {
        "f_statistic": float(f_stat),
        "p_value": float(p_val),
        "n_genes": int(len(counts)),
        "n_samples": int(counts.shape[1]),
        "groups": [str(g) for g in groups],
    }


def per_gene_fold_change(counts, meta, group_col, group_a, group_b):
    """Compute per-gene log2 fold change between two groups, then median.

    Returns dict: {median_log2fc, mean_log2fc, n_genes, group_a, group_b,
    n_samples_a, n_samples_b, n_abs_fc_gt_1}.
    """
    samples_a = meta[meta[group_col] == group_a].index
    samples_b = meta[meta[group_col] == group_b].index

    mean_a = counts[samples_a].mean(axis=1)
    mean_b = counts[samples_b].mean(axis=1)

    # Avoid log(0): add pseudocount
    pseudo = 1.0
    log2fc = np.log2((mean_a + pseudo) / (mean_b + pseudo))

    median_fc = np.median(log2fc)
    mean_fc = np.mean(log2fc)
    n_big = int((np.abs(log2fc) > 1).sum())

    print(f"Group A ({group_a}): {len(samples_a)} samples")
    print(f"Group B ({group_b}): {len(samples_b)} samples")
    print(f"Genes: {len(log2fc)}")
    print(f"Median log2FC: {median_fc:.4f}")
    print(f"Mean log2FC: {mean_fc:.4f}")
    print(f"Genes with |log2FC| > 1: {n_big}")
    return {
        "median_log2fc": float(median_fc),
        "mean_log2fc": float(mean_fc),
        "n_genes": int(len(log2fc)),
        "group_a": str(group_a),
        "group_b": str(group_b),
        "n_samples_a": int(len(samples_a)),
        "n_samples_b": int(len(samples_b)),
        "n_abs_log2fc_gt_1": n_big,
    }


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

        try:
            counts, meta, gcol, groups = load_data(
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
                result = per_gene_anova(counts, meta, gcol, groups)
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
            result = per_gene_fold_change(counts, meta, gcol, resolved_a, resolved_b)
        except Exception as exc:  # noqa: BLE001
            return {"status": "error", "error": f"Fold-change failed: {exc}"}
        return {"status": "success", "data": result}
