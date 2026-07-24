#!/usr/bin/env python3
"""Stereochemistry tracker through reaction sequences.

Tracks R/S configuration at a stereocenter through a series of common
organic reaction types, predicting the stereochemical outcome at each step.

Supported reaction types:
  SN2          - backside attack: inversion of configuration
  SN1          - carbocation intermediate: racemization
  E2           - elimination: destroys stereocenter (sp2 product)
  E1           - elimination: destroys stereocenter (sp2 product)
  reduction    - typically retention (no bond to stereocenter broken)
  oxidation    - typically retention (no bond to stereocenter broken)
  retention    - explicit retention (e.g., SNi, some metal-catalyzed)
  inversion    - explicit inversion (for custom reactions)
  racemization - explicit racemization (e.g., epimerization, enolization)
  double_inversion - two sequential inversions = retention (e.g., Mitsunobu)
  walden       - synonym for inversion (Walden inversion)

Usage examples:
  python stereochem_tracker.py --start R --reactions SN2
  python stereochem_tracker.py --start S --reactions "SN2, SN2"
  python stereochem_tracker.py --start R --reactions "SN2, oxidation, SN1"
  python stereochem_tracker.py --start S --reactions "retention, SN2, reduction, SN2"
  python stereochem_tracker.py --start R --reactions "double_inversion, SN2"
"""

import argparse
import sys

# Each reaction maps to its stereochemical effect
REACTION_EFFECTS = {
    "SN2": "inversion",
    "sn2": "inversion",
    "SN1": "racemization",
    "sn1": "racemization",
    "E2": "elimination",
    "e2": "elimination",
    "E1": "elimination",
    "e1": "elimination",
    "reduction": "retention",
    "oxidation": "retention",
    "retention": "retention",
    "sni": "retention",
    "SNi": "retention",
    "inversion": "inversion",
    "walden": "inversion",
    "racemization": "racemization",
    "epimerization": "racemization",
    "enolization": "racemization",
    "double_inversion": "retention",
    "mitsunobu": "inversion",  # net inversion (acid displaces DIAD adduct via SN2)
    "hydrogenation": "retention",
    "hydroboration": "retention",  # syn addition, retention at existing centers
    "epoxidation": "retention",  # no bond to stereocenter broken
}

REACTION_EXPLANATIONS = {
    "SN2": "Backside attack forces inversion of configuration (Walden inversion)",
    "SN1": "Planar carbocation intermediate allows attack from both faces -> racemization",
    "E2": "Elimination produces sp2 carbon, destroying the stereocenter",
    "E1": "Elimination produces sp2 carbon, destroying the stereocenter",
    "reduction": "No bond to stereocenter is broken; configuration retained",
    "oxidation": "No bond to stereocenter is broken; configuration retained",
    "retention": "Configuration explicitly retained",
    "inversion": "Configuration explicitly inverted",
    "racemization": "Stereocenter is destroyed and reformed without selectivity",
    "double_inversion": "Two inversions cancel out, giving net retention",
    "mitsunobu": "DIAD/PPh3 activates OH with inversion, then acid SN2 = net inversion",
    "walden": "Walden inversion: backside displacement inverts configuration",
    "sni": "Internal return mechanism: retention of configuration",
    "epimerization": "Reversible opening at stereocenter produces mixture",
    "enolization": "Enolate is planar; reprotonation gives racemic mixture",
    "hydrogenation": "Catalytic H2 addition does not break bonds at existing stereocenters",
    "hydroboration": "Syn addition; existing stereocenters retain configuration",
    "epoxidation": "Concerted mechanism; existing stereocenters retain configuration",
}


def invert(config):
    """Invert R to S or S to R."""
    if config == "R":
        return "S"
    if config == "S":
        return "R"
    return config


def apply_reaction(config, reaction):
    """Apply a reaction to the current configuration.

    Returns (new_config, effect, explanation).
    new_config is 'R', 'S', 'racemic', or 'eliminated'.
    """
    key = reaction.strip()
    effect = REACTION_EFFECTS.get(key)
    if effect is None:
        # Try case-insensitive lookup
        effect = REACTION_EFFECTS.get(key.lower())
    if effect is None:
        return config, "unknown", f"Unknown reaction type '{key}'; configuration unchanged (manual check needed)"

    explanation = REACTION_EXPLANATIONS.get(key, REACTION_EXPLANATIONS.get(key.lower(), ""))

    if config in ("racemic", "eliminated"):
        if effect == "elimination":
            return "eliminated", effect, explanation
        if config == "eliminated":
            return "eliminated", effect, "Stereocenter already eliminated; reaction has no stereochemical effect here"
        # racemic stays racemic for retention/inversion; stays racemic for racemization
        if effect == "inversion":
            return "racemic", effect, explanation + " (but starting material is racemic, so product remains racemic)"
        return "racemic", effect, explanation + " (starting material is racemic)"

    if effect == "inversion":
        return invert(config), effect, explanation
    if effect == "racemization":
        return "racemic", effect, explanation
    if effect == "elimination":
        return "eliminated", effect, explanation
    if effect == "retention":
        return config, effect, explanation

    return config, effect, explanation


def track_sequence(start, reactions):
    """Track stereochemistry through a sequence of reactions.

    Returns list of step dicts.
    """
    steps = []
    current = start
    for i, rxn in enumerate(reactions):
        rxn = rxn.strip()
        if not rxn:
            continue
        new_config, effect, explanation = apply_reaction(current, rxn)
        steps.append({
            "step": i + 1,
            "reaction": rxn,
            "effect": effect,
            "before": current,
            "after": new_config,
            "explanation": explanation,
        })
        current = new_config
    return steps


def print_results(start, steps):
    """Pretty-print the tracking results."""
    print(f"Starting configuration: {start}")
    print("-" * 60)
    for s in steps:
        print(f"Step {s['step']}: {s['reaction']}")
        print(f"  Effect:      {s['effect']}")
        print(f"  {s['before']} -> {s['after']}")
        print(f"  Reason:      {s['explanation']}")
        print()

    if steps:
        final = steps[-1]["after"]
        print("=" * 60)
        print(f"FINAL RESULT: {final}")
        if final == "racemic":
            print("  The product is a racemic mixture (equal R and S).")
        elif final == "eliminated":
            print("  The stereocenter has been eliminated (sp2 carbon).")
        else:
            print(f"  The product has {final} configuration at the tracked center.")

        # Count inversions for summary
        inversions = sum(1 for s in steps if s["effect"] == "inversion")
        if inversions > 0 and final not in ("racemic", "eliminated"):
            parity = "odd" if inversions % 2 == 1 else "even"
            print(f"  ({inversions} inversion(s) total [{parity}] -> net {'inversion' if inversions % 2 == 1 else 'retention'})")


def main():
    parser = argparse.ArgumentParser(
        description="Track stereochemistry (R/S) through a reaction sequence."
    )
    parser.add_argument(
        "--start", required=True, choices=["R", "S"],
        help="Starting configuration (R or S)"
    )
    parser.add_argument(
        "--reactions", required=True, type=str,
        help='Comma-separated reaction types, e.g. "SN2, oxidation, SN1"'
    )
    parser.add_argument(
        "--list-reactions", action="store_true",
        help="List all supported reaction types and exit"
    )
    args = parser.parse_args()

    if args.list_reactions:
        print("Supported reaction types:")
        seen = set()
        for key in REACTION_EFFECTS:
            if key.lower() not in seen:
                effect = REACTION_EFFECTS[key]
                expl = REACTION_EXPLANATIONS.get(key, "")
                print(f"  {key:20s} -> {effect:15s}  {expl}")
                seen.add(key.lower())
        return 0

    reactions = [r.strip() for r in args.reactions.split(",") if r.strip()]
    if not reactions:
        print("Error: no reactions provided.", file=sys.stderr)
        return 1

    steps = track_sequence(args.start, reactions)
    print_results(args.start, steps)
    return 0


if __name__ == "__main__":
    sys.exit(main())
