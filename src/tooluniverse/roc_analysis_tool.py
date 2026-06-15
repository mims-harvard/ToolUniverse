"""
ROC / AUC diagnostic-accuracy analysis for ToolUniverse.

Local-compute, deterministic ROC analysis for any binary classifier or
continuous biomarker: given scores and 0/1 labels, returns AUC (with a
bootstrap 95% CI), the Youden-optimal cutoff and its sensitivity/specificity,
optionally the metrics at a user-supplied fixed cutoff, and a downsampled ROC
curve. Backed by scikit-learn. No network, no API key.

Generic by construction — it takes scores + labels (inline arrays or two
columns of a CSV), exposes the positive label and cutoff as parameters, and
returns the standard sklearn result. It encodes no task-specific convention.
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
    meta = {"engine": "scikit-learn"}
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


@register_tool("ROCAnalysisTool")
class ROCAnalysisTool(BaseTool):
    """Deterministic ROC/AUC analysis over scores + binary labels."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            import numpy as np
            from sklearn.metrics import roc_auc_score, roc_curve
        except Exception:  # pragma: no cover - dependency guard
            return _err(
                "scikit-learn / numpy not installed. `pip install scikit-learn`."
            )

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
            auc = float(roc_auc_score(y, s))
            fpr, tpr, thr = roc_curve(y, s)
        except Exception as e:
            return _err(f"ROC computation failed: {e}")

        # Youden-optimal operating point.
        youden = tpr - fpr
        j = int(np.argmax(youden))
        opt = {
            "cutoff": float(thr[j]),
            "sensitivity": round(float(tpr[j]), 6),
            "specificity": round(float(1 - fpr[j]), 6),
        }

        data: Dict[str, Any] = {
            "auc": round(auc, 6),
            "auc_ci95": self._bootstrap_ci(y, s, np, roc_auc_score),
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
    def _bootstrap_ci(y, s, np, roc_auc_score) -> Optional[List[float]]:
        """Deterministic bootstrap 95% CI for AUC (fixed seed)."""
        rng = np.random.default_rng(_BOOTSTRAP_SEED)
        idx = np.arange(y.size)
        aucs = []
        for _ in range(_BOOTSTRAP_N):
            b = rng.choice(idx, size=y.size, replace=True)
            if len(np.unique(y[b])) < 2:
                continue
            aucs.append(roc_auc_score(y[b], s[b]))
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
            # thr[0] is sklearn's +inf sentinel; report as a large finite number.
            "thresholds": [
                (round(float(thr[i]), 6) if thr[i] != float("inf") else None)
                for i in keep
            ],
        }
