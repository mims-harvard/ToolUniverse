#!/usr/bin/env python3
"""Side-by-side synergy reference expectations for the
tooluniverse-drug-synergy skill.

Given the single-agent and combination fractional inhibition at one dose pair,
prints the Bliss, HSA, and simple-additive expected combination effects and the
corresponding synergy scores, so you can see at a glance whether the reference
models agree before running the full DrugSynergy_* tools (which also handle
dose-response models Loewe / CI / ZIP).

Inputs are FRACTIONAL inhibition (0-1). For % viability, convert first:
inhibition = 1 - viability/100.

Usage:
  python synergy_reference.py --ea 0.4 --eb 0.3 --ecombo 0.7
"""

import argparse


def _call(score):
    if score > 0.10:
        return "synergy"
    if score < -0.10:
        return "antagonism"
    return "additive"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ea", type=float, required=True, help="fractional inhibition of drug A (0-1)")
    ap.add_argument("--eb", type=float, required=True, help="fractional inhibition of drug B (0-1)")
    ap.add_argument("--ecombo", type=float, required=True, help="fractional inhibition of A+B (0-1)")
    args = ap.parse_args()

    ea, eb, ec = args.ea, args.eb, args.ecombo
    for v, name in ((ea, "ea"), (eb, "eb"), (ec, "ecombo")):
        if not 0 <= v <= 1:
            raise SystemExit(f"{name}={v} is not a fraction in [0,1]; convert % viability to 1-viability/100.")

    bliss_exp = ea + eb - ea * eb
    hsa_exp = max(ea, eb)
    additive_exp = min(1.0, ea + eb)

    print(f"\nObserved combination effect: {ec:.3f}  (single agents: A={ea:.3f}, B={eb:.3f})\n")
    print(f"{'Model':<26}{'expected':>10}{'score':>10}   call")
    for name, exp in (
        ("Bliss independence", bliss_exp),
        ("HSA (highest single)", hsa_exp),
        ("Simple additive (capped)", additive_exp),
    ):
        score = ec - exp
        print(f"{name:<26}{exp:>10.3f}{score:>10.3f}   {_call(score)}")

    if ec >= 0.95 and min(ea, eb) >= 0.9:
        print("\n  ! both single agents near-complete inhibition — ceiling effect; little headroom to detect synergy.")
    print("\nFor Loewe / Combination Index / ZIP (dose-response or matrix models) use the DrugSynergy_* tools.")


if __name__ == "__main__":
    main()
