"""
ROC / AUC diagnostic-accuracy analysis for ToolUniverse.

Local-compute, deterministic ROC analysis for any binary classifier or
continuous biomarker: given scores and 0/1 labels, returns AUC (with a
bootstrap 95% CI), the Youden-optimal cutoff and its sensitivity/specificity,
optionally the metrics at a user-supplied fixed cutoff, and a downsampled ROC
curve. Pure NumPy (a core dependency) — no scikit-learn, no network, no API key,
so it runs on a default install.

AUC is the tie-aware Mann-Whitney rank-sum statistic, which equals
``sklearn.metrics.roc_auc_score`` exactly. The ROC curve uses the standard
descending-score sweep with distinct-score thresholds, matching ``roc_curve``.

Generic by construction — it takes scores + labels (inline arrays or two
columns of a CSV), exposes the positive label and cutoff as parameters, and
returns the standard ROC result. It encodes no task-specific convention.
"""

import csv as _csv
import os
from typing import Any, Dict, List, Optional

from .base_tool import BaseTool
from .tool_registry import register_tool

_BOOTSTRAP_N = 2000
_BOOTSTRAP_SEED = 0
_MAX_CURVE_POINTS = 100


def _err(msg: str) -> Dict[str, Any]:
    return {"status": "error", "error": msg}


def _ok(data: Dict[str, Any], **metadata) -> Dict[str, Any]:
    meta = {"engine": "numpy"}
    meta.update(metadata)
    return {"status": "success", "data": data, "metadata": meta}


def _load_from_csv(
    path: str, score_col: Optional[str], label_col: Optional[str]
) -> Any:
    """Return (scores, labels) lists from a CSV, or an error dict."""
    path = os.path.expanduser(str(path).strip())
    if not os.path.isfile(path):
        return _err(f"csv_path not found: {path}")
    try:
        with open(path, newline="") as fh:
            reader = _csv.DictReader(fh)
            fields = reader.fieldnames or []
            sc = score_col or ("score" if "score" in fields else None)
            lc = label_col or ("label" if "label" in fields else None)
            if sc not in fields or lc not in fields:
                return _err(
                    f"score_col/label_col not found. Have columns {fields}; "
                    f"asked for score={sc!r}, label={lc!r}"
                )
            scores, labels = [], []
            for row in reader:
                scores.append(row[sc])
                labels.append(row[lc])
        return scores, labels
    except Exception as e:  # pragma: no cover - defensive
        return _err(f"failed to read csv_path: {e}")


def _coerce(scores: List[Any], labels: List[Any], positive_label: Any) -> Any:
    """Coerce raw scores/labels to (float scores, 0/1 int labels), or error dict."""
    if scores is None or labels is None:
        return _err("Provide both 'scores' and 'labels' (inline), or 'csv_path'.")
    if len(scores) != len(labels):
        return _err(
            f"scores and labels length mismatch: {len(scores)} vs {len(labels)}"
        )
    if len(scores) < 2:
        return _err("Need at least 2 observations.")
    try:
        s = [float(x) for x in scores]
    except (TypeError, ValueError):
        return _err("All scores must be numeric.")

    if positive_label is not None:
        y = [1 if str(v) == str(positive_label) else 0 for v in labels]
    else:
        # Accept 0/1, '0'/'1', or two-class labels mapped by sorted order.
        uniq = sorted(set(str(v) for v in labels))
        if set(uniq) <= {"0", "1"}:
            y = [1 if str(v) == "1" else 0 for v in labels]
        elif len(uniq) == 2:
            # Map the lexicographically larger class to 1; caller can override
            # with positive_label for clarity.
            pos = uniq[1]
            y = [1 if str(v) == pos else 0 for v in labels]
        else:
            return _err(
                f"labels must be binary (got {len(uniq)} classes: {uniq}). "
                f"Pass 'positive_label' to define the positive class."
            )
    if sum(y) == 0 or sum(y) == len(y):
        return _err("labels must contain both a positive and a negative class.")
    return s, y


def _avg_ranks(values, np):
    """1-based ranks with ties resolved to their average (midranks)."""
    order = np.argsort(values, kind="mergesort")
    sorted_vals = values[order]
    ranks_sorted = np.empty(len(values), dtype=float)
    i = 0
    n = len(values)
    while i < n:
        j = i
        while j + 1 < n and sorted_vals[j + 1] == sorted_vals[i]:
            j += 1
        ranks_sorted[i : j + 1] = (i + j) / 2.0 + 1.0  # mean of 1-based ranks
        i = j + 1
    ranks = np.empty(n, dtype=float)
    ranks[order] = ranks_sorted
    return ranks


def _auc(y, s, np) -> float:
    """Tie-aware AUC via the Mann-Whitney rank sum (== sklearn roc_auc_score)."""
    n_pos = int(y.sum())
    n_neg = int(y.size - n_pos)
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    ranks = _avg_ranks(s, np)
    sum_ranks_pos = ranks[y == 1].sum()
    return (sum_ranks_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)


def _roc_curve(y, s, np):
    """Standard ROC sweep. Returns (fpr, tpr, thresholds) like sklearn.roc_curve."""
    order = np.argsort(-s, kind="mergesort")
    s_sorted, y_sorted = s[order], y[order]
    tps = np.cumsum(y_sorted)
    fps = np.cumsum(1 - y_sorted)
    # Collapse points that share a score: keep the last index of each run.
    distinct = np.where(np.diff(s_sorted) != 0)[0]
    idxs = np.r_[distinct, s_sorted.size - 1]
    tps, fps, thr = tps[idxs], fps[idxs], s_sorted[idxs]
    tpr = tps / tps[-1]
    fpr = fps / fps[-1]
    # Prepend the (0,0) origin with an +inf threshold, as sklearn does.
    return (
        np.r_[0.0, fpr],
        np.r_[0.0, tpr],
        np.r_[np.inf, thr],
    )


@register_tool("ROCAnalysisTool")
class ROCAnalysisTool(BaseTool):
    """Deterministic ROC/AUC analysis over scores + binary labels (pure NumPy)."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            import numpy as np
        except Exception:  # pragma: no cover - dependency guard
            return _err("numpy not installed (it is a core ToolUniverse dependency).")

        scores = arguments.get("scores")
        labels = arguments.get("labels")
        if arguments.get("csv_path"):
            loaded = _load_from_csv(
                arguments["csv_path"],
                arguments.get("score_col"),
                arguments.get("label_col"),
            )
            if isinstance(loaded, dict):
                return loaded
            scores, labels = loaded

        coerced = _coerce(scores, labels, arguments.get("positive_label"))
        if isinstance(coerced, dict):
            return coerced
        s_list, y_list = coerced
        s = np.asarray(s_list, dtype=float)
        y = np.asarray(y_list, dtype=int)

        try:
            auc = _auc(y, s, np)
            fpr, tpr, thr = _roc_curve(y, s, np)
        except Exception as e:  # pragma: no cover - defensive
            return _err(f"ROC computation failed: {e}")

        # Youden-optimal operating point.
        j = int(np.argmax(tpr - fpr))
        opt = {
            "cutoff": float(thr[j]),
            "sensitivity": round(float(tpr[j]), 6),
            "specificity": round(float(1 - fpr[j]), 6),
        }

        data: Dict[str, Any] = {
            "auc": round(float(auc), 6),
            "auc_ci95": self._bootstrap_ci(y, s, np),
            "n": int(y.size),
            "n_positive": int(y.sum()),
            "n_negative": int(y.size - y.sum()),
            "youden_optimal": opt,
            "roc_curve": self._downsample_curve(fpr, tpr, thr),
        }

        cutoff = arguments.get("cutoff")
        if cutoff is not None:
            try:
                c = float(cutoff)
            except (TypeError, ValueError):
                return _err(f"'cutoff' must be a number, got {cutoff!r}")
            pred = s >= c
            pos, neg = y == 1, y == 0
            tp = int((pred & pos).sum())
            fn = int((~pred & pos).sum())
            tn = int((~pred & neg).sum())
            fp = int((pred & neg).sum())
            data["at_cutoff"] = {
                "cutoff": c,
                "sensitivity": round(tp / (tp + fn), 6) if (tp + fn) else None,
                "specificity": round(tn / (tn + fp), 6) if (tn + fp) else None,
            }
        return _ok(data)

    @staticmethod
    def _bootstrap_ci(y, s, np) -> Optional[List[float]]:
        """Deterministic bootstrap 95% CI for AUC (fixed seed)."""
        rng = np.random.default_rng(_BOOTSTRAP_SEED)
        idx = np.arange(y.size)
        aucs = []
        for _ in range(_BOOTSTRAP_N):
            b = rng.choice(idx, size=y.size, replace=True)
            if len(np.unique(y[b])) < 2:
                continue
            aucs.append(_auc(y[b], s[b], np))
        if not aucs:
            return None
        lo, hi = np.percentile(aucs, [2.5, 97.5])
        return [round(float(lo), 6), round(float(hi), 6)]

    @staticmethod
    def _downsample_curve(fpr, tpr, thr) -> Dict[str, List[float]]:
        """Return the ROC curve, thinned to at most _MAX_CURVE_POINTS points."""
        n = len(fpr)
        if n <= _MAX_CURVE_POINTS:
            keep = range(n)
        else:
            step = n / _MAX_CURVE_POINTS
            keep = sorted({int(i * step) for i in range(_MAX_CURVE_POINTS)} | {n - 1})
        return {
            "fpr": [round(float(fpr[i]), 6) for i in keep],
            "tpr": [round(float(tpr[i]), 6) for i in keep],
            # The leading threshold is the +inf origin sentinel; report as null.
            "thresholds": [
                (round(float(thr[i]), 6) if thr[i] != float("inf") else None)
                for i in keep
            ],
        }
