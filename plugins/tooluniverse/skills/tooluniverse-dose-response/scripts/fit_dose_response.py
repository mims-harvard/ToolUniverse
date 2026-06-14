#!/usr/bin/env python3
"""4-parameter logistic (Hill) dose-response fit for the
tooluniverse-dose-response skill.

Reads a CSV of concentration,response[,replicate columns], fits the 4PL model
  f(x) = Emin + (Emax - Emin) / (1 + (EC50/x)^n)
and reports IC50/EC50, Hill slope, Emax, Emin, r^2, and a 95% CI on the IC50.
Matches DoseResponse_calculate_ic50; use this when you need normalization,
replicate averaging, or a text curve that the tool doesn't provide.

CSV columns: concentration, response   (one row per measurement; replicates at
the same concentration are averaged). Optionally --normalize with a control and
blank to convert raw signal to % response.

Usage:
  python fit_dose_response.py --input data.csv
  python fit_dose_response.py --input raw.csv --normalize --control 12000 --blank 200
"""

import argparse
import csv
import math

import numpy as np
from scipy.optimize import curve_fit


def hill_4pl(x, emin, emax, ec50, n):
    return emin + (emax - emin) / (1 + (ec50 / x) ** n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="CSV: concentration,response")
    ap.add_argument("--normalize", action="store_true", help="convert raw signal to % of control")
    ap.add_argument("--control", type=float, help="raw signal of the 100% control (with --normalize)")
    ap.add_argument("--blank", type=float, default=0.0, help="raw blank/background (with --normalize)")
    args = ap.parse_args()

    pairs = {}
    with open(args.input, newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                c = float(row["concentration"])
                r = float(row["response"])
            except (KeyError, ValueError):
                continue
            if c <= 0:  # log(0) undefined; drop zero-concentration rows
                continue
            pairs.setdefault(c, []).append(r)

    if len(pairs) < 4:
        raise SystemExit("Need >=4 distinct positive concentrations to fit a 4PL curve.")

    conc = np.array(sorted(pairs))
    resp = np.array([float(np.mean(pairs[c])) for c in conc])
    if args.normalize:
        if args.control is None:
            raise SystemExit("--normalize requires --control (raw 100% signal).")
        resp = 100.0 * (resp - args.blank) / (args.control - args.blank)

    # Initial guesses: plateaus from the data, EC50 at the geometric midpoint.
    p0 = [float(resp.min()), float(resp.max()), float(np.exp(np.mean(np.log(conc)))), 1.0]
    popt, pcov = curve_fit(hill_4pl, conc, resp, p0=p0, maxfev=20000)
    emin, emax, ec50, n = popt
    perr = np.sqrt(np.diag(pcov))
    ci = (ec50 - 1.96 * perr[2], ec50 + 1.96 * perr[2])

    pred = hill_4pl(conc, *popt)
    ss_res = float(np.sum((resp - pred) ** 2))
    ss_tot = float(np.sum((resp - resp.mean()) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot else float("nan")

    print(f"\n4PL dose-response fit ({len(conc)} concentrations)\n")
    print(f"{'Conc':>12}{'Response':>12}{'Fitted':>12}")
    for c, ro, pr in zip(conc, resp, pred):
        print(f"{c:>12g}{ro:>12.2f}{pr:>12.2f}")
    print("-" * 36)
    # Report plateaus by position (top/bottom) so labels are unambiguous for
    # both inhibition (high->low) and activation (low->high) curves.
    top, bottom = max(emin, emax), min(emin, emax)
    print(f"IC50/EC50 = {ec50:.4g}   95% CI [{ci[0]:.4g}, {ci[1]:.4g}]  (concentration units of the input)")
    print(f"Hill slope |n| = {abs(n):.3f}   top plateau = {top:.2f}   bottom plateau = {bottom:.2f}   r^2 = {r2:.4f}")

    # Quality gates the skill asks us to surface.
    if not (conc.min() <= ec50 <= conc.max()):
        print("  ! IC50 falls OUTSIDE the tested range — curve is incomplete; widen concentrations.")
    if r2 < 0.90:
        print("  ! r^2 < 0.90 — poor fit; check for outliers, biphasic data, or wrong model.")
    if abs(n) > 4:
        print(f"  ! |Hill slope|={abs(n):.1f} is very steep — usually too few transition points, not real cooperativity.")


if __name__ == "__main__":
    main()
