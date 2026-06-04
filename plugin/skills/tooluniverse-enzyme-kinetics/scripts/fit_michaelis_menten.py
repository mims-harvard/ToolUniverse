#!/usr/bin/env python3
"""Michaelis-Menten nonlinear fit for the tooluniverse-enzyme-kinetics skill.

Reads a substrate-velocity CSV, fits v = Vmax*[S]/(Km+[S]) by nonlinear
regression (matching EnzymeKinetics_calculate's nonlinear_fit), and — when an
enzyme concentration is given — converts Vmax to kcat and kcat/Km. Prefer this
over the Lineweaver-Burk linearization for reported values.

CSV columns: substrate, velocity   (one row per measurement; replicates at the
same [S] are averaged).

Usage:
  python fit_michaelis_menten.py --input kinetics.csv
  python fit_michaelis_menten.py --input kinetics.csv --enzyme-conc 5e-9   # molar, for kcat
"""

import argparse
import csv

import numpy as np
from scipy.optimize import curve_fit


def mm(s, vmax, km):
    return vmax * s / (km + s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="CSV: substrate,velocity")
    ap.add_argument(
        "--enzyme-conc",
        type=float,
        default=None,
        help="total enzyme concentration (molar) to convert Vmax->kcat",
    )
    args = ap.parse_args()

    pairs = {}
    with open(args.input, newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                s = float(row["substrate"])
                v = float(row["velocity"])
            except (KeyError, ValueError):
                continue
            if s < 0:
                continue
            pairs.setdefault(s, []).append(v)

    if len(pairs) < 4:
        raise SystemExit("Need >=4 distinct substrate concentrations.")

    s = np.array(sorted(pairs))
    v = np.array([float(np.mean(pairs[x])) for x in s])

    p0 = [float(v.max()) * 1.2, float(np.median(s))]
    popt, _ = curve_fit(mm, s, v, p0=p0, maxfev=20000, bounds=(0, np.inf))
    vmax, km = popt
    pred = mm(s, *popt)
    ss_res = float(np.sum((v - pred) ** 2))
    ss_tot = float(np.sum((v - v.mean()) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot else float("nan")

    print(f"\nMichaelis-Menten nonlinear fit ({len(s)} points)\n")
    print(f"{'[S]':>12}{'v':>12}{'fitted':>12}{'resid':>10}")
    for si, vi, pi in zip(s, v, pred):
        print(f"{si:>12g}{vi:>12.3f}{pi:>12.3f}{vi - pi:>10.3f}")
    print("-" * 46)
    print(f"Vmax = {vmax:.4g}   Km = {km:.4g} (same units as [S])   R^2 = {r2:.4f}")
    print(f"catalytic efficiency (Vmax/Km) = {vmax / km:.4g}")

    if args.enzyme_conc:
        kcat = vmax / args.enzyme_conc
        print(f"kcat = Vmax/[E] = {kcat:.4g} s^-1   kcat/Km = {kcat / km:.4g} (per [S]-unit)·s^-1")

    if not (s.min() <= km <= s.max()):
        print("  ! Km falls OUTSIDE the tested [S] range — widen substrate concentrations.")
    if r2 < 0.98:
        print("  ! R^2 < 0.98 — check residuals for curvature (substrate inhibition / wrong model).")
    # systematic residual sign pattern hints at a non-MM shape (e.g. substrate inhibition)
    signs = np.sign(v - pred)
    if len(signs) >= 6 and np.sum(signs[: len(signs) // 2]) * np.sum(signs[len(signs) // 2 :]) < -1:
        print("  ! residuals change sign systematically across [S] — MM may be the wrong model.")


if __name__ == "__main__":
    main()
