#!/usr/bin/env python3
"""Meta-analysis helper for the tooluniverse-meta-analysis skill.

Reads a CSV of study results, converts each row to an (effect_size, SE) pair on
an additive scale, and pools them with fixed- and random-effects (DerSimonian-
Laird) models — matching MetaAnalysis_run. Prints per-study weights, the pooled
estimate (back-transformed to the ratio scale when inputs were ratios), the
heterogeneity statistics, and a text forest plot.

Supported CSV column sets (pick the one matching your data; 'name' always):
  ratio + CI:        name, or, ci_low, ci_high      (or use rr/hr instead of or)
  log/linear scale:  name, beta, se
  two-group means:   name, mean1, sd1, n1, mean2, sd2, n2   -> Hedges' g
  correlation:       name, r, n                     -> Fisher z

Usage:
  python meta_analysis.py --input studies.csv [--method random|fixed]
"""

import argparse
import csv
import math


def _ci_to_se(point_log: float, lo_log: float, hi_log: float, z: float = 1.96) -> float:
    return (hi_log - lo_log) / (2 * z)


def _row_to_effect(row: dict):
    """Return (effect_size, se, is_ratio) on the additive (log, for ratios) scale."""
    g = {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()}

    # Already on the additive scale.
    if g.get("beta") not in (None, "") and g.get("se") not in (None, ""):
        return float(g["beta"]), float(g["se"]), False

    # Ratio measure (OR / RR / HR) with a 95% CI -> log scale.
    for key in ("or", "rr", "hr", "ratio"):
        if g.get(key) not in (None, ""):
            point = float(g[key])
            lo, hi = float(g["ci_low"]), float(g["ci_high"])
            return math.log(point), _ci_to_se(*map(math.log, (point, lo, hi))), True

    # Two-group means -> Hedges' g (standardized mean difference, bias-corrected).
    if g.get("mean1") not in (None, ""):
        m1, s1, n1 = float(g["mean1"]), float(g["sd1"]), float(g["n1"])
        m2, s2, n2 = float(g["mean2"]), float(g["sd2"]), float(g["n2"])
        sp = math.sqrt(((n1 - 1) * s1**2 + (n2 - 1) * s2**2) / (n1 + n2 - 2))
        d = (m1 - m2) / sp
        J = 1 - 3 / (4 * (n1 + n2) - 9)  # small-sample correction
        gval = J * d
        se = math.sqrt((n1 + n2) / (n1 * n2) + gval**2 / (2 * (n1 + n2)))
        return gval, se, False

    # Pearson correlation -> Fisher z.
    if g.get("r") not in (None, ""):
        r, n = float(g["r"]), float(g["n"])
        return math.atanh(r), 1 / math.sqrt(n - 3), False

    raise ValueError(f"Row '{g.get('name')}' has no recognized effect-size columns.")


def pool(effects, ses, method):
    w = [1 / s**2 for s in ses]
    eff_fixed = sum(e * wi for e, wi in zip(effects, w)) / sum(w)
    Q = sum(wi * (e - eff_fixed) ** 2 for e, wi in zip(effects, w))
    df = len(effects) - 1
    I2 = max(0.0, (Q - df) / Q * 100) if Q > 0 else 0.0
    # DerSimonian-Laird between-study variance.
    C = sum(w) - sum(wi**2 for wi in w) / sum(w)
    tau2 = max(0.0, (Q - df) / C) if C > 0 else 0.0

    if method == "random":
        w = [1 / (s**2 + tau2) for s in ses]
    pooled = sum(e * wi for e, wi in zip(effects, w)) / sum(w)
    pooled_se = math.sqrt(1 / sum(w))
    weights_pct = [wi / sum(w) * 100 for wi in w]
    return pooled, pooled_se, weights_pct, Q, df, I2, tau2


def _bar(lo, hi, point, span_lo, span_hi, width=40):
    def pos(x):
        return int((x - span_lo) / (span_hi - span_lo) * (width - 1))

    line = [" "] * width
    for i in range(pos(lo), pos(hi) + 1):
        if 0 <= i < width:
            line[i] = "-"
    if 0 <= pos(point) < width:
        line[pos(point)] = "#"
    return "".join(line)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="CSV of study results")
    ap.add_argument("--method", choices=["random", "fixed"], default="random")
    args = ap.parse_args()

    with open(args.input, newline="") as fh:
        rows = list(csv.DictReader(fh))
    if len(rows) < 2:
        raise SystemExit("Need at least 2 studies to pool.")

    names, effects, ses, ratio_flags = [], [], [], []
    for row in rows:
        e, s, is_ratio = _row_to_effect(row)
        names.append(row.get("name") or f"Study {len(names) + 1}")
        effects.append(e)
        ses.append(s)
        ratio_flags.append(is_ratio)
    is_ratio = any(ratio_flags)

    pooled, pooled_se, wpct, Q, df, I2, tau2 = pool(effects, ses, args.method)
    lo, hi = pooled - 1.96 * pooled_se, pooled + 1.96 * pooled_se
    z = pooled / pooled_se
    # two-sided p via the normal survival function without scipy
    p = math.erfc(abs(z) / math.sqrt(2))

    tr = (lambda x: math.exp(x)) if is_ratio else (lambda x: x)
    label = "OR/RR/HR" if is_ratio else "effect"
    study_lo = [tr(e - 1.96 * s) for e, s in zip(effects, ses)]
    study_hi = [tr(e + 1.96 * s) for e, s in zip(effects, ses)]
    span_lo = min(study_lo + [tr(lo)])
    span_hi = max(study_hi + [tr(hi)])

    print(f"\nMeta-analysis ({args.method}-effects), {len(names)} studies, scale={label}\n")
    print(f"{'Study':<22}{'Est':>8}{'95% CI':>20}{'Wt%':>7}   forest")
    for n, e, s, w in zip(names, effects, ses, wpct):
        el, eh = tr(e - 1.96 * s), tr(e + 1.96 * s)
        bar = _bar(el, eh, tr(e), span_lo, span_hi)
        print(f"{n[:21]:<22}{tr(e):>8.3f}{f'[{el:.2f}, {eh:.2f}]':>20}{w:>6.1f}  |{bar}|")
    print("-" * 80)
    diamond = _bar(tr(lo), tr(hi), tr(pooled), span_lo, span_hi)
    print(f"{'POOLED':<22}{tr(pooled):>8.3f}{f'[{tr(lo):.2f}, {tr(hi):.2f}]':>20}{'':>6}  |{diamond}|")
    print(
        f"\npooled {label} = {tr(pooled):.4f}  95% CI [{tr(lo):.4f}, {tr(hi):.4f}]  "
        f"z={z:.3f}  p={p:.3e}"
    )
    print(f"heterogeneity: Q={Q:.3f} (df={df}), I^2={I2:.1f}%, tau^2={tau2:.4f}")
    if I2 > 75:
        print("  ! I^2 > 75%: considerable heterogeneity — pooling may mislead; explain why studies differ.")
    elif I2 > 50:
        print("  random-effects recommended; consider subgroup / meta-regression.")
    if len(names) < 10:
        print("  note: <10 studies — publication-bias (funnel/Egger) cannot be reliably assessed.")


if __name__ == "__main__":
    main()
