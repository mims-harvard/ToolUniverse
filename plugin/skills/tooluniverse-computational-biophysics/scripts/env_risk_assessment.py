"""
Environmental risk assessment calculator for contaminated site exposure.

Computes hazard quotient (HQ) for human exposure to soil contaminants
via food ingestion pathway (soil → soil solution → plant → human).

Calculation steps:
  1. Soil concentration: C_soil = total_mass / soil_mass
  2. Soil-water partitioning: C_sw = C_soil * rho_b / (Kd * rho_b + theta_w)
     where Kd = foc * Koc
  3. Plant uptake: C_plant = C_sw * TSCF * PUF
  4. Daily intake: DI = C_plant * intake_rate_g * bioavailability
  5. Average daily dose: ADD = total_DI / body_weight
  6. Hazard quotient: HQ = ADD / RfD

Key parameter notes:
  - Koc (organic carbon partition coefficient) is compound-specific.
    Common values: PFHxS ~36, PFOS ~200, PFOA ~70 L/kg.
  - TSCF (transpiration stream concentration factor): dimensionless,
    typically 0.1-10 for different compounds.
  - PUF (plant uptake factor): fraction of root-zone contaminant
    transferred to edible parts.

Usage:
    # Basic: single food pathway
    python env_risk_assessment.py \\
        --total_mass_ug 1e9 --area_m2 250000 --depth_m 0.6 \\
        --bulk_density 1500 --theta_w 0.35 --foc 0.03 --Koc 36 \\
        --food "fruit:300:0.5:0.1:5" \\
        --body_weight 80 --RfD 0.02

    # Multiple food pathways
    python env_risk_assessment.py \\
        --total_mass_ug 1e9 --area_m2 250000 --depth_m 0.6 \\
        --bulk_density 1500 --theta_w 0.35 --foc 0.03 --Koc 36 \\
        --food "fruit:300:0.5:0.1:5" --food "legume:50:0.3:0.2:5" \\
        --body_weight 80 --RfD 0.02

    Food format: "name:intake_g_per_day:bioavailability:plant_uptake_factor:TSCF"
"""

import argparse
import sys


def compute_soil_concentration(total_mass_ug: float, area_m2: float,
                                depth_m: float, bulk_density_kg_m3: float) -> float:
    """Soil concentration in ug/kg. C_soil = total_mass / (area * depth * rho_b)."""
    soil_mass_kg = area_m2 * depth_m * bulk_density_kg_m3
    return total_mass_ug / soil_mass_kg


def compute_soil_solution(C_soil_ug_kg: float, bulk_density: float,
                           theta_w: float, Kd: float) -> float:
    """
    Soil solution (pore water) concentration in ug/L.
    C_sw = C_soil * rho_b / (Kd * rho_b + theta_w)
    Note: rho_b in kg/m3, theta_w in L/L (= m3/m3), Kd in L/kg.
    Result: ug/m3 internally, converted to ug/L by dividing by 1000.
    """
    # C_soil [ug/kg] * rho_b [kg/m3] = ug/m3 in bulk soil
    # Kd*rho_b [L/kg * kg/m3 = L/m3], theta_w [L/L = L/(0.001 m3)]
    # Denominator: Kd*rho_b + theta_w  (in consistent units)
    # For the partition: C_sw(ug/L) = C_soil(ug/kg) * rho_b(kg/L) / (Kd(L/kg)*rho_b(kg/L) + theta_w(L/L))
    # rho_b in kg/L = rho_b_kg_m3 / 1000
    rho_b_kg_L = bulk_density / 1000.0
    C_sw = C_soil_ug_kg * rho_b_kg_L / (Kd * rho_b_kg_L + theta_w)
    return C_sw


def compute_daily_intake(C_sw_ug_L: float, TSCF: float, PUF: float,
                          intake_g_day: float, bioavailability: float) -> float:
    """
    Daily intake in ug/day from one food pathway.
    DI = C_sw * TSCF * PUF * intake_g * bioavailability
    """
    return C_sw_ug_L * TSCF * PUF * intake_g_day * bioavailability


def compute_hazard_quotient(total_DI_ug_day: float, body_weight_kg: float,
                             RfD_ug_kg_day: float) -> float:
    """HQ = (DI / BW) / RfD."""
    ADD = total_DI_ug_day / body_weight_kg
    return ADD / RfD_ug_kg_day


def parse_food(food_str: str) -> dict:
    """Parse food specification: 'name:intake_g:bioavailability:PUF:TSCF'."""
    parts = food_str.split(":")
    if len(parts) != 5:
        raise ValueError(
            f"Food must have 5 colon-separated fields "
            f"(name:intake_g:bioavailability:PUF:TSCF), got: {food_str}"
        )
    return {
        "name": parts[0],
        "intake_g": float(parts[1]),
        "bioavailability": float(parts[2]),
        "PUF": float(parts[3]),
        "TSCF": float(parts[4]),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Environmental risk assessment: hazard quotient from soil contamination.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--total_mass_ug", type=float, required=True,
                        help="Total contaminant mass in soil (ug).")
    parser.add_argument("--area_m2", type=float, required=True,
                        help="Contaminated area (m2).")
    parser.add_argument("--depth_m", type=float, required=True,
                        help="Contamination depth (m).")
    parser.add_argument("--bulk_density", type=float, required=True,
                        help="Soil bulk density (kg/m3).")
    parser.add_argument("--theta_w", type=float, required=True,
                        help="Volumetric water content (L water / L soil).")
    parser.add_argument("--foc", type=float, required=True,
                        help="Fraction organic carbon in soil (0-1).")
    parser.add_argument("--Koc", type=float, required=True,
                        help="Organic carbon partition coefficient (L/kg).")
    parser.add_argument("--food", action="append", required=True,
                        help="Food pathway: 'name:intake_g:bioavailability:PUF:TSCF'. "
                             "Can be specified multiple times.")
    parser.add_argument("--body_weight", type=float, required=True,
                        help="Body weight (kg).")
    parser.add_argument("--RfD", type=float, required=True,
                        help="Reference dose (ug/kg body weight/day).")
    args = parser.parse_args()

    # Parse food pathways
    foods = []
    for f_str in args.food:
        try:
            foods.append(parse_food(f_str))
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    # Step 1: Soil concentration
    C_soil = compute_soil_concentration(
        args.total_mass_ug, args.area_m2, args.depth_m, args.bulk_density
    )
    soil_mass = args.area_m2 * args.depth_m * args.bulk_density

    # Step 2: Soil-water partition
    Kd = args.foc * args.Koc
    C_sw = compute_soil_solution(C_soil, args.bulk_density, args.theta_w, Kd)

    # Step 3-4: Daily intake per food pathway
    food_results = []
    total_DI = 0.0
    for food in foods:
        DI = compute_daily_intake(C_sw, food["TSCF"], food["PUF"],
                                   food["intake_g"], food["bioavailability"])
        food_results.append({**food, "DI": DI})
        total_DI += DI

    # Step 5-6: Dose and HQ
    ADD = total_DI / args.body_weight
    HQ = compute_hazard_quotient(total_DI, args.body_weight, args.RfD)

    # --- Output ---
    print("=" * 65)
    print("  Environmental Risk Assessment — Hazard Quotient")
    print("=" * 65)

    print()
    print("  Step 1: Soil Concentration")
    print(f"    Total contaminant  : {args.total_mass_ug:.2e} ug")
    print(f"    Area               : {args.area_m2:,.0f} m2")
    print(f"    Depth              : {args.depth_m} m")
    print(f"    Bulk density       : {args.bulk_density} kg/m3")
    print(f"    Soil mass          : {soil_mass:,.0f} kg")
    print(f"    C_soil = {args.total_mass_ug:.2e} / {soil_mass:.2e}")
    print(f"           = {C_soil:.4f} ug/kg")

    print()
    print("  Step 2: Soil Solution Concentration (Kd-corrected)")
    print(f"    foc = {args.foc},  Koc = {args.Koc} L/kg")
    print(f"    Kd = foc * Koc = {Kd:.4f} L/kg")
    print(f"    theta_w = {args.theta_w} L/L")
    rho_b_L = args.bulk_density / 1000.0
    print(f"    rho_b = {rho_b_L:.3f} kg/L")
    denom = Kd * rho_b_L + args.theta_w
    print(f"    C_sw = C_soil * rho_b / (Kd*rho_b + theta_w)")
    print(f"         = {C_soil:.4f} * {rho_b_L:.3f} / ({Kd:.4f}*{rho_b_L:.3f} + {args.theta_w})")
    print(f"         = {C_soil * rho_b_L:.4f} / {denom:.4f}")
    print(f"         = {C_sw:.4f} ug/L")

    print()
    print("  Step 3-4: Daily Intake by Food Pathway")
    for fr in food_results:
        print(f"    {fr['name']}:")
        print(f"      Intake = {fr['intake_g']:.0f} g/day,  BF = {fr['bioavailability']},  "
              f"PUF = {fr['PUF']},  TSCF = {fr['TSCF']}")
        print(f"      DI = {C_sw:.4f} * {fr['TSCF']} * {fr['PUF']} * {fr['intake_g']:.0f} * {fr['bioavailability']}")
        print(f"         = {fr['DI']:.4f} ug/day")
    print(f"    ----------------------------------------")
    print(f"    Total daily intake = {total_DI:.4f} ug/day")

    print()
    print("  Step 5: Average Daily Dose")
    print(f"    ADD = {total_DI:.4f} / {args.body_weight} = {ADD:.4f} ug/kg/day")

    print()
    print("  Step 6: Hazard Quotient")
    print(f"    RfD = {args.RfD} ug/kg/day")
    print(f"    HQ  = ADD / RfD = {ADD:.4f} / {args.RfD}")
    print(f"        = {HQ:.1f}")
    print()

    if HQ > 1:
        print(f"    RESULT: HQ = {HQ:.1f} >> 1 — significant health risk.")
    else:
        print(f"    RESULT: HQ = {HQ:.2f} < 1 — within acceptable risk level.")

    print()
    print("  Verification:")
    HQ_check = (C_sw * sum(f["TSCF"] * f["PUF"] * f["intake_g"] * f["bioavailability"]
                            for f in foods)) / args.body_weight / args.RfD
    print(f"    HQ recomputed: {HQ_check:.1f}  (matches: {abs(HQ_check - HQ) < 0.1})")
    print("=" * 65)


if __name__ == "__main__":
    main()
