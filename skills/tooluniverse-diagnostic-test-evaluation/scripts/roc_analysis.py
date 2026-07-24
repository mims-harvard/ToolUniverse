#!/usr/bin/env python3
"""ROC / AUC / optimal-cutoff analysis for the
tooluniverse-diagnostic-test-evaluation skill.

Reads a CSV of (label, score), computes the ROC AUC with a bootstrap 95% CI,
finds the Youden-optimal cutoff and its sensitivity/specificity, and prints a
text ROC curve. For the fixed-cutoff 2x2 metrics use Epidemiology_diagnostic;
for post-test probability use Epidemiology_bayesian.

CSV columns: label (1=disease/positive, 0=healthy/negative), score (continuous).

Usage:
  python roc_analysis.py --input scores.csv
"""

import argparse
import csv

import numpy as np
from sklearn.metrics import roc_auc_score, roc_curve


def bootstrap_auc_ci(y, s, n=2000, seed=0):
    rng = np.random.default_rng(seed)
    idx = np.arange(len(y))
    aucs = []
    for _ in range(n):
        b = rng.choice(idx, size=len(idx), replace=True)
        if len(np.unique(y[b])) < 2:
            continue
        aucs.append(roc_auc_score(y[b], s[b]))
    if not aucs:
        return (float("nan"), float("nan"))
    return tuple(np.percentile(aucs, [2.5, 97.5]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="CSV: label,score")
    args = ap.parse_args()

    ys, ss = [], []
    with open(args.input, newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                ys.append(int(float(row["label"])))
                ss.append(float(row["score"]))
            except (KeyError, ValueError):
                continue
    y, s = np.array(ys), np.array(ss)
    if len(np.unique(y)) < 2:
        raise SystemExit("Need both positive (1) and negative (0) labels.")

    auc = roc_auc_score(y, s)
    lo, hi = bootstrap_auc_ci(y, s)
    fpr, tpr, thr = roc_curve(y, s)
    youden = tpr - fpr
    j = int(np.argmax(youden))
    cutoff, sens, spec = thr[j], tpr[j], 1 - fpr[j]

    band = (
        "outstanding" if auc > 0.9 else
        "excellent" if auc > 0.8 else
        "acceptable" if auc > 0.7 else
        "poor/near-chance"
    )
    print(f"\nROC analysis: {len(y)} samples ({int(y.sum())} positive, {int((1 - y).sum())} negative)\n")
    print(f"AUC = {auc:.3f}  95% CI [{lo:.3f}, {hi:.3f}]  ({band})")
    print(f"Youden-optimal cutoff: score >= {cutoff:.4g}  ->  sensitivity {sens:.3f}, specificity {spec:.3f}")

    # text ROC curve
    print("\nROC (TPR vs FPR):")
    grid = np.linspace(0, 1, 11)
    tpr_at = np.interp(grid, fpr, tpr)
    for g, t in zip(grid[::-1], tpr_at[::-1]):
        bar = "#" * int(round(t * 40))
        print(f"  FPR={g:.1f} | {bar:<40} TPR={t:.2f}")
    if auc < 0.7:
        print("\n  ! AUC < 0.7 — weak discrimination.")
    if y.mean() < 0.1 or y.mean() > 0.9:
        print("  ! strong class imbalance — also report PPV at the real prevalence (precision-recall is informative).")


if __name__ == "__main__":
    main()
