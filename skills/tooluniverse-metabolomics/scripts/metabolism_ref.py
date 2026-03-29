#!/usr/bin/env python3
"""Metabolism reference: pathways, isotope tracers, ATP yields."""
import argparse, json, sys

# --- 1. Central metabolism pathway data ---
PATHWAYS = {
    "glycolysis": {
        "name": "Glycolysis", "location": "cytoplasm",
        "input": "glucose", "output": "2 pyruvate",
        "net_atp": 2, "nadh": 2, "fadh2": 0, "gtp": 0, "steps": 10,
        "key_enzymes": ["hexokinase", "PFK-1", "aldolase", "pyruvate kinase"],
        "irreversible_steps": ["hexokinase (step 1)", "PFK-1 (step 3)", "pyruvate kinase (step 10)"],
        "notes": "Glucose (6C) split by aldolase into G3P+DHAP (3C each). Net = 2 ATP, 2 NADH, 2 pyruvate.",
    },
    "tca": {
        "name": "TCA cycle (Krebs cycle)", "location": "mitochondrial matrix",
        "input": "acetyl-CoA (2C) + oxaloacetate (4C)", "output": "2 CO2 + oxaloacetate (regenerated)",
        "net_atp": 0, "nadh": 3, "fadh2": 1, "gtp": 1, "steps": 8,
        "key_enzymes": ["citrate synthase", "isocitrate dehydrogenase", "alpha-ketoglutarate dehydrogenase", "succinate dehydrogenase"],
        "irreversible_steps": ["citrate synthase", "isocitrate dehydrogenase", "alpha-ketoglutarate dehydrogenase"],
        "notes": "Per turn: 3 NADH + 1 FADH2 + 1 GTP. Per glucose (2 acetyl-CoA): multiply by 2.",
    },
    "oxidative_phosphorylation": {
        "name": "Oxidative phosphorylation", "location": "inner mitochondrial membrane",
        "input": "NADH, FADH2, O2", "output": "ATP, H2O",
        "conversion": {"NADH": 2.5, "FADH2": 1.5},
        "notes": "NADH -> Complex I -> ~2.5 ATP. FADH2 -> Complex II -> ~1.5 ATP. Varies by shuttle.",
    },
    "pentose_phosphate_pathway": {
        "name": "Pentose phosphate pathway (PPP)", "location": "cytoplasm",
        "input": "glucose-6-phosphate", "output": "ribose-5-phosphate + 2 NADPH + CO2",
        "phases": {"oxidative": "G6P -> ribulose-5-P + 2 NADPH + CO2 (irreversible)",
                   "non-oxidative": "ribulose-5-P <-> ribose-5-P, fructose-6-P, G3P (reversible)"},
        "notes": "C1 of glucose released as CO2 in oxidative phase. Primary NADPH and ribose-5-P source.",
    },
    "gluconeogenesis": {
        "name": "Gluconeogenesis", "location": "cytoplasm + mitochondria",
        "input": "2 pyruvate", "output": "glucose", "cost": "4 ATP + 2 GTP + 2 NADH",
        "bypass_enzymes": ["pyruvate carboxylase", "PEP carboxykinase",
                           "fructose-1,6-bisphosphatase", "glucose-6-phosphatase"],
        "notes": "Not simply reverse glycolysis; uses 4 bypass reactions.",
    },
    "beta_oxidation": {
        "name": "Fatty acid beta-oxidation", "location": "mitochondrial matrix",
        "input": "fatty acyl-CoA", "output": "acetyl-CoA units + NADH + FADH2",
        "per_round": {"NADH": 1, "FADH2": 1, "acetyl_CoA": 1},
        "notes": "Cn fatty acid: (n/2-1) rounds, n/2 acetyl-CoA, (n/2-1) FADH2+NADH. Activation costs 2 ATP.",
    },
}

# --- 2. Isotope tracer data ---
GLUCOSE_CARBON_FATES = {
    "C1": "Released as CO2 in PPP oxidative phase; in glycolysis -> C3 of pyruvate",
    "C2": "Becomes C2 of pyruvate -> methyl carbon of acetyl-CoA",
    "C3": "Becomes C1 of pyruvate (carbonyl) -> released as CO2 by pyruvate dehydrogenase",
    "C4": "Becomes C1 of pyruvate (carbonyl) -> released as CO2 by pyruvate dehydrogenase",
    "C5": "Becomes C2 of pyruvate -> methyl carbon of acetyl-CoA",
    "C6": "Released as CO2 in PPP oxidative phase; in glycolysis -> C3 of pyruvate",
}
TRACER_RULES = {
    "first_CO2_release": "C3/C4 released first (pyruvate decarboxylation). C1/C6 first if glucose enters PPP.",
    "acetyl_CoA_carbons": "C2 and C5 of glucose become the two carbons of acetyl group in acetyl-CoA.",
    "ppp_CO2": "C1 of glucose -> CO2 in the oxidative phase of PPP.",
    "tca_CO2_first_turn": "First TCA turn: CO2 from oxaloacetate carbons, not incoming acetyl-CoA. Acetyl carbons released in later turns.",
}


def parse_labeled_carbons(substrate_str: str) -> list[int]:
    """Extract labeled carbon positions from e.g. '1,4-13C-glucose'."""
    carbons = []
    for p in substrate_str.replace(" ", "").split("-"):
        if "13C" in p.upper() or p.lower() in ("glucose", "pyruvate", "acetylcoa"):
            continue
        for num in p.split(","):
            if num.isdigit():
                carbons.append(int(num))
    return sorted(carbons)


def trace_carbons(substrate_str: str, pathway: str) -> dict:
    """Trace 13C-labeled carbons through a pathway."""
    carbons = parse_labeled_carbons(substrate_str)
    if not carbons:
        return {"error": f"Could not parse labeled carbons from '{substrate_str}'"}
    fates = [{"carbon": f"C{c}", "fate": GLUCOSE_CARBON_FATES.get(f"C{c}", f"No data for C{c}")} for c in carbons]
    co2, retained = [], []
    if pathway in ("glycolysis", "tca", "pyruvate_dehydrogenase"):
        for c in carbons:
            if c in (3, 4):
                co2.append(f"C{c} -> CO2 via pyruvate decarboxylation")
            elif c in (2, 5):
                retained.append(f"C{c} -> acetyl-CoA (enters TCA)")
            elif c in (1, 6):
                retained.append(f"C{c} -> C3 of pyruvate (stays in carbon skeleton)")
    elif pathway in ("ppp", "pentose_phosphate_pathway"):
        for c in carbons:
            if c == 1:
                co2.append(f"C{c} -> CO2 in PPP oxidative phase")
            else:
                retained.append(f"C{c} -> remains in sugar phosphate skeleton")
    return {
        "substrate": substrate_str, "labeled_carbons": carbons, "pathway": pathway,
        "carbon_fates": fates, "rules": TRACER_RULES,
        "co2_release": co2 or ["None of the labeled carbons released as CO2 in this pathway"],
        "retained": retained,
    }


# --- 3. ATP yield calculations ---
def atp_glucose(conditions: str) -> dict:
    """ATP yield from complete glucose oxidation."""
    if conditions == "anaerobic":
        return {"substrate": "glucose", "conditions": "anaerobic (fermentation)",
                "total_atp": 2, "breakdown": {"glycolysis_net": 2},
                "notes": "Pyruvate -> lactate (or ethanol); NADH recycled, not oxidized."}
    bd = {"glycolysis_net_atp": 2,
          "glycolysis_nadh": {"count": 2, "atp_each": 2.5, "subtotal": 5.0},
          "pyruvate_dehydrogenase_nadh": {"count": 2, "atp_each": 2.5, "subtotal": 5.0},
          "tca_nadh": {"count": 6, "atp_each": 2.5, "subtotal": 15.0},
          "tca_fadh2": {"count": 2, "atp_each": 1.5, "subtotal": 3.0},
          "tca_gtp": {"count": 2, "atp_each": 1.0, "subtotal": 2.0}}
    total = sum(v["subtotal"] if isinstance(v, dict) else v for v in bd.values())
    return {"substrate": "glucose", "conditions": "aerobic", "total_atp": total,
            "range": "30-32 ATP (shuttle-dependent)", "breakdown": bd,
            "notes": "Malate-aspartate shuttle: ~32 ATP. Glycerol-3-phosphate shuttle: ~30 ATP."}


KNOWN_FATTY_ACIDS = {
    "palmitate": 16, "palmitoyl": 16, "palmitic": 16,
    "stearate": 18, "stearic": 18, "myristate": 14, "myristic": 14,
    "laurate": 12, "lauric": 12, "oleate": 18, "oleic": 18,
}


def atp_fatty_acid(name: str, carbons: int, conditions: str) -> dict:
    """ATP yield from fatty acid beta-oxidation + TCA."""
    if conditions == "anaerobic":
        return {"error": "Fatty acid oxidation requires O2 (aerobic only)."}
    rounds = carbons // 2 - 1
    acetyl_coa = carbons // 2
    activation_cost = 2
    total_nadh = rounds + acetyl_coa * 3
    total_fadh2 = rounds + acetyl_coa
    total_gtp = acetyl_coa
    gross = total_nadh * 2.5 + total_fadh2 * 1.5 + total_gtp
    return {"substrate": name, "carbons": carbons, "conditions": "aerobic",
            "beta_oxidation_rounds": rounds, "acetyl_CoA_produced": acetyl_coa,
            "activation_cost_atp": activation_cost,
            "total_nadh": total_nadh, "total_fadh2": total_fadh2, "total_gtp": total_gtp,
            "gross_atp": gross, "net_atp": gross - activation_cost}


def calc_atp(substrate: str, conditions: str) -> dict:
    """Route ATP calculation based on substrate."""
    sub = substrate.lower().strip()
    if sub == "glucose":
        return atp_glucose(conditions)
    fa_carbons = KNOWN_FATTY_ACIDS.get(sub)
    if fa_carbons:
        return atp_fatty_acid(substrate, fa_carbons, conditions)
    return {"error": f"Unknown substrate '{substrate}'. Known: glucose, {', '.join(sorted(KNOWN_FATTY_ACIDS))}"}


# --- CLI ---
def main():
    p = argparse.ArgumentParser(description="Metabolism reference tool")
    p.add_argument("--type", required=True, choices=["pathway", "tracer", "atp"])
    p.add_argument("--name", help="Pathway name (for --type pathway)")
    p.add_argument("--substrate", help="Substrate (for --type tracer/atp)")
    p.add_argument("--pathway", help="Pathway to trace through (for --type tracer)")
    p.add_argument("--conditions", default="aerobic", choices=["aerobic", "anaerobic"])
    args = p.parse_args()

    if args.type == "pathway":
        name = (args.name or "").lower().replace(" ", "_")
        result = PATHWAYS.get(name, {"error": f"Unknown pathway '{args.name}'", "available": list(PATHWAYS)})
    elif args.type == "tracer":
        if not args.substrate:
            result = {"error": "--substrate required for tracer mode"}
        else:
            result = trace_carbons(args.substrate, (args.pathway or "glycolysis").lower().replace(" ", "_"))
    elif args.type == "atp":
        if not args.substrate:
            result = {"error": "--substrate required for atp mode"}
        else:
            result = calc_atp(args.substrate, args.conditions)
    else:
        result = {"error": "Invalid type"}
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
