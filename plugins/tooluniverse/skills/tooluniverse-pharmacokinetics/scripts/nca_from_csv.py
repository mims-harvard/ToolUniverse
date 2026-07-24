#!/usr/bin/env python3
"""Non-compartmental PK analysis from a concentration-time CSV, for the
tooluniverse-pharmacokinetics skill.

Computes Cmax, Tmax, AUC0-last, AUC0-inf, terminal lambda_z / half-life, CL,
Vd, and the % AUC extrapolated — using the FDA/EMA linear-up / log-down
trapezoidal rule, matching NCA_compute_parameters. Use for CSV profiles or
when you need explicit BLQ handling.

CSV columns: time, concentration   (one row per sample; BLQ as empty or 'BLQ').
Leading BLQs become 0; trailing BLQs in the terminal tail are dropped.

Usage:
  python nca_from_csv.py --input profile.csv --dose 100 --route iv
"""

import argparse
import csv
import math


def _read(path):
    times, concs = [], []
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                t = float(row["time"])
            except (KeyError, ValueError):
                continue
            raw = (row.get("concentration") or "").strip()
            c = None if raw == "" or raw.upper() == "BLQ" else float(raw)
            times.append(t)
            concs.append(c)
    return times, concs


def _clean_blq(times, concs):
    # Leading BLQ -> 0; drop trailing/interior None (terminal BLQ corrupts slope).
    seen_measurable = False
    out_t, out_c = [], []
    for t, c in sorted(zip(times, concs)):
        if c is None:
            if not seen_measurable:
                out_t.append(t)
                out_c.append(0.0)
            # else: drop terminal BLQ
        else:
            seen_measurable = True
            out_t.append(t)
            out_c.append(c)
    return out_t, out_c


def _auc_linlog(t, c):
    """Linear-up / log-down trapezoidal AUC."""
    auc = 0.0
    for i in range(1, len(t)):
        dt = t[i] - t[i - 1]
        c0, c1 = c[i - 1], c[i]
        if c1 >= c0 or c0 <= 0 or c1 <= 0:
            auc += dt * (c0 + c1) / 2  # linear (up, or any zero)
        else:
            auc += dt * (c0 - c1) / math.log(c0 / c1)  # log (down)
    return auc


def _terminal(t, c, n_min=3):
    """Regress ln(C) on t over the last >=3 positive points; return lambda_z, r^2, n."""
    pts = [(ti, ci) for ti, ci in zip(t, c) if ci > 0]
    best = None
    for k in range(n_min, len(pts) + 1):
        sub = pts[-k:]
        xs = [p[0] for p in sub]
        ys = [math.log(p[1]) for p in sub]
        n = len(sub)
        mx, my = sum(xs) / n, sum(ys) / n
        sxx = sum((x - mx) ** 2 for x in xs)
        sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        if sxx == 0:
            continue
        slope = sxy / sxx
        if slope >= 0:
            continue
        yhat = [my + slope * (x - mx) for x in xs]
        ss_res = sum((y - yh) ** 2 for y, yh in zip(ys, yhat))
        ss_tot = sum((y - my) ** 2 for y in ys)
        r2 = 1 - ss_res / ss_tot if ss_tot else 0
        if best is None or r2 > best[1]:
            best = (-slope, r2, n)
    return best  # (lambda_z, r2, n) or None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--dose", type=float, required=True)
    ap.add_argument("--route", default="iv", choices=["iv", "po", "oral"])
    args = ap.parse_args()

    t, c = _clean_blq(*_read(args.input))
    if len(t) < 4:
        raise SystemExit("Need >=4 measurable concentration-time points.")

    cmax = max(c)
    tmax = t[c.index(cmax)]
    auc_last = _auc_linlog(t, c)
    clast = next(ci for ci in reversed(c) if ci > 0)

    term = _terminal(t, c)
    print(f"\nNCA ({args.route.upper()}), {len(t)} points\n")
    print(f"Cmax = {cmax:.4g}   Tmax = {tmax:.4g}")
    print(f"AUC0-last = {auc_last:.4g}")
    if term:
        lz, r2, n = term
        thalf = math.log(2) / lz
        auc_inf = auc_last + clast / lz
        extrap = (auc_inf - auc_last) / auc_inf * 100
        cl = args.dose / auc_inf
        vd = cl / lz
        apparent = "" if args.route == "iv" else "/F (apparent)"
        print(f"lambda_z = {lz:.4g} (terminal r^2={r2:.4f}, n={n})   t_half = {thalf:.4g}")
        print(f"AUC0-inf = {auc_inf:.4g}   extrapolated = {extrap:.1f}%")
        print(f"CL{apparent} = {cl:.4g}   Vd{apparent} = {vd:.4g}")
        if extrap > 20:
            print("  ! AUC extrapolation > 20% — AUC0-inf / CL / Vd unreliable; report AUC0-last and sample longer.")
        if r2 < 0.9 or n < 3:
            print("  ! terminal fit weak (r^2<0.9 or <3 points) — half-life unreliable.")
        if args.route != "iv":
            print("  note: oral data -> CL and Vd are apparent (CL/F, Vd/F), not true clearance/volume.")
    else:
        print("  ! could not define a terminal elimination phase (no >=3 declining positive points).")


if __name__ == "__main__":
    main()
