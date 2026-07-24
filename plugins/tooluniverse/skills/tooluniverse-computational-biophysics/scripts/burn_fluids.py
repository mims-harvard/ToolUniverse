"""
Burn resuscitation fluid calculator.

Supports three resuscitation formulas:

1. Parkland (Baxter) formula — adults and older children:
    Total 24h = 4 * weight_kg * %TBSA   [mL of Lactated Ringer's]
    First 8h  : half the total (from TIME OF BURN, not admission)
    Next 16h  : other half

2. Modified Brooke formula — alternative for adults/pediatrics:
    Total 24h = 2 * weight_kg * %TBSA   [mL of LR]
    First 8h  : half the total
    Next 16h  : other half
    For pediatric patients: add maintenance fluids (4-2-1 rule) on top.

3. Galveston formula — pediatric (BSA-based):
    Total 24h = 5000 * BSA_m2 * (%TBSA / 100) + 2000 * BSA_m2
    (resuscitation component + maintenance component)
    First 8h  : half the total
    Next 16h  : other half

Pediatric maintenance fluids (4-2-1 rule, added to Parkland/Brooke for children):
    First 10 kg  : 4 mL/kg/h
    Next 10 kg   : 2 mL/kg/h
    Each kg > 20 : 1 mL/kg/h

Holliday-Segar maintenance fluid (daily method, shown for reference):
    <= 10 kg : 100 mL/kg/day
    10-20 kg : 1000 + 50 mL/kg/day above 10 kg
    > 20 kg  : 1500 + 20 mL/kg/day above 20 kg

Second 24h (not auto-calculated here):
    Colloid: 0.3-0.5 mL/kg/%TBSA  (start at ~18-24 h)
    Free water to maintain urine output 0.5-1 mL/kg/h

Usage:
    # Adult (80 kg, 40% TBSA) — Parkland (default for >= 30 kg):
    python burn_fluids.py --weight_kg 80 --tbsa_pct 40

    # Pediatric, modified Brooke + maintenance (25 kg, 45% TBSA):
    python burn_fluids.py --weight_kg 25 --age_years 7 --tbsa_pct 45 --formula brooke

    # Pediatric, Galveston (25 kg, 45% TBSA, BSA 0.95 m2):
    python burn_fluids.py --weight_kg 25 --age_years 7 --tbsa_pct 45 --bsa_m2 0.95

    # Adult, modified Brooke:
    python burn_fluids.py --weight_kg 80 --tbsa_pct 40 --formula brooke
"""

import argparse
import sys


def maintenance_4_2_1(weight_kg: float) -> dict:
    """
    Maintenance fluid rate by the 4-2-1 rule (hourly method).
    Returns hourly rate (mL/h) and daily equivalent (mL/day).

    First 10 kg  : 4 mL/kg/h
    Next 10 kg   : 2 mL/kg/h
    Each kg > 20 : 1 mL/kg/h
    """
    if weight_kg <= 10:
        hourly = 4.0 * weight_kg
    elif weight_kg <= 20:
        hourly = 40.0 + 2.0 * (weight_kg - 10.0)
    else:
        hourly = 60.0 + 1.0 * (weight_kg - 20.0)
    return {"hourly_mL_per_h": hourly, "daily_mL": hourly * 24.0}


def holliday_segar(weight_kg: float) -> dict:
    """
    Maintenance fluid by Holliday-Segar method (daily method).
    Returns daily (mL/day) and hourly (mL/h) rates.
    """
    if weight_kg <= 10:
        daily = 100.0 * weight_kg
    elif weight_kg <= 20:
        daily = 1000.0 + 50.0 * (weight_kg - 10.0)
    else:
        daily = 1500.0 + 20.0 * (weight_kg - 20.0)
    return {"daily_mL": daily, "hourly_mL_per_h": daily / 24.0}


def parkland(weight_kg: float, tbsa_pct: float) -> dict:
    """
    Parkland (Baxter) formula for burn resuscitation.
    Total 24h = 4 * weight_kg * %TBSA mL of LR.
    """
    total_24h = 4.0 * weight_kg * tbsa_pct
    first_8h_total = total_24h / 2.0
    next_16h_total = total_24h / 2.0
    return {
        "formula": "Parkland",
        "coefficient": 4,
        "total_24h_mL": total_24h,
        "first_8h_mL": first_8h_total,
        "next_16h_mL": next_16h_total,
        "rate_first_8h_mL_per_h": first_8h_total / 8.0,
        "rate_next_16h_mL_per_h": next_16h_total / 16.0,
    }


def modified_brooke(weight_kg: float, tbsa_pct: float) -> dict:
    """
    Modified Brooke formula for burn resuscitation.
    Total 24h = 2 * weight_kg * %TBSA mL of LR.
    """
    total_24h = 2.0 * weight_kg * tbsa_pct
    first_8h_total = total_24h / 2.0
    next_16h_total = total_24h / 2.0
    return {
        "formula": "Modified Brooke",
        "coefficient": 2,
        "total_24h_mL": total_24h,
        "first_8h_mL": first_8h_total,
        "next_16h_mL": next_16h_total,
        "rate_first_8h_mL_per_h": first_8h_total / 8.0,
        "rate_next_16h_mL_per_h": next_16h_total / 16.0,
    }


def galveston(bsa_m2: float, tbsa_pct: float) -> dict:
    """
    Galveston formula for pediatric burn resuscitation.
    Total 24h = 5000 * BSA_m2 * (%TBSA/100) + 2000 * BSA_m2 mL of LR.
    """
    resuscitation_component = 5000.0 * bsa_m2 * (tbsa_pct / 100.0)
    maintenance_component = 2000.0 * bsa_m2
    total_24h = resuscitation_component + maintenance_component
    first_8h_total = total_24h / 2.0
    next_16h_total = total_24h / 2.0
    return {
        "formula": "Galveston",
        "resuscitation_component_mL": resuscitation_component,
        "maintenance_component_mL": maintenance_component,
        "total_24h_mL": total_24h,
        "first_8h_mL": first_8h_total,
        "next_16h_mL": next_16h_total,
        "rate_first_8h_mL_per_h": first_8h_total / 8.0,
        "rate_next_16h_mL_per_h": next_16h_total / 16.0,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Burn resuscitation fluid calculator (Parkland / Modified Brooke / Galveston).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--weight_kg", type=float, required=True, help="Patient weight in kg.")
    parser.add_argument(
        "--tbsa_pct",
        type=float,
        required=True,
        help="Total body surface area burned (%%TBSA), e.g. 45 for 45%%.",
    )
    parser.add_argument(
        "--age_years", type=float, default=None, help="Patient age in years (triggers pediatric mode if < 14)."
    )
    parser.add_argument(
        "--bsa_m2",
        type=float,
        default=None,
        help="Body surface area in m2 (required for Galveston formula).",
    )
    parser.add_argument(
        "--formula",
        choices=["parkland", "brooke", "galveston"],
        default=None,
        help="Resuscitation formula: parkland (4 mL/kg/%%TBSA), brooke (2 mL/kg/%%TBSA), "
        "galveston (BSA-based, pediatric). Default: galveston if pediatric + BSA given, "
        "else parkland for adults.",
    )
    args = parser.parse_args()

    weight = args.weight_kg
    tbsa = args.tbsa_pct

    # Validate inputs
    if weight <= 0:
        print("Error: weight_kg must be positive.")
        sys.exit(1)
    if not (0 < tbsa <= 100):
        print(f"Error: tbsa_pct must be between 0 and 100 (got {tbsa}).")
        sys.exit(1)
    if args.bsa_m2 is not None and args.bsa_m2 <= 0:
        print(f"Error: bsa_m2 must be positive (got {args.bsa_m2}).")
        sys.exit(1)

    # Determine if pediatric
    is_pediatric = (args.age_years is not None and args.age_years < 14) or weight < 30

    # Determine formula
    if args.formula is not None:
        formula = args.formula
    elif is_pediatric and args.bsa_m2 is not None:
        formula = "galveston"
    elif is_pediatric:
        formula = "brooke"
    else:
        formula = "parkland"

    if formula == "galveston" and args.bsa_m2 is None:
        print("Error: --bsa_m2 is required for the Galveston formula.")
        print("  Provide patient BSA in m2, or use --formula parkland/brooke.")
        sys.exit(1)

    print("=" * 62)
    print("  Burn Resuscitation Fluid Calculator")
    print("=" * 62)
    age_str = f"{args.age_years} y" if args.age_years is not None else "not specified"
    pop_str = "Pediatric" if is_pediatric else "Adult"
    print(f"  Weight       : {weight} kg")
    print(f"  Age          : {age_str}")
    print(f"  %TBSA burned : {tbsa}%")
    if args.bsa_m2 is not None:
        print(f"  BSA          : {args.bsa_m2} m2")
    print(f"  Population   : {pop_str}")

    # ---- Compute resuscitation ----
    if formula == "galveston":
        r = galveston(args.bsa_m2, tbsa)
    elif formula == "brooke":
        r = modified_brooke(weight, tbsa)
    else:
        r = parkland(weight, tbsa)

    # ---- Display formula details ----
    print()
    if formula == "galveston":
        print("  Galveston Formula (LR):")
        print(f"    Resuscitation component : {r['resuscitation_component_mL']:.1f} mL")
        print(f"      = 5000 x {args.bsa_m2} m2 x {tbsa / 100:.2f}")
        print(f"    Maintenance component   : {r['maintenance_component_mL']:.1f} mL")
        print(f"      = 2000 x {args.bsa_m2} m2")
    elif formula == "brooke":
        print("  Modified Brooke Formula (LR):")
        print(f"    Total = 2 x {weight} kg x {tbsa}% = {r['total_24h_mL']:.1f} mL")
    else:
        print("  Parkland Formula (LR):")
        print(f"    Total = 4 x {weight} kg x {tbsa}% = {r['total_24h_mL']:.1f} mL")

    # ---- Maintenance for pediatric (Parkland/Brooke only) ----
    maint_hourly = 0.0
    add_maintenance = is_pediatric and formula != "galveston"
    if add_maintenance:
        m = maintenance_4_2_1(weight)
        maint_hourly = m["hourly_mL_per_h"]

    # Combined rates
    resus_first_8h = r["rate_first_8h_mL_per_h"]
    resus_next_16h = r["rate_next_16h_mL_per_h"]
    total_first_8h_rate = resus_first_8h + maint_hourly
    total_next_16h_rate = resus_next_16h + maint_hourly

    print()
    print("  +---------------------------------------------------------+")
    print(f"  |  Total resuscitation 24h : {r['total_24h_mL']:>8.1f} mL                |")
    print(f"  |  First 8h  (half)        : {r['first_8h_mL']:>8.1f} mL                |")
    print(f"  |    resuscitation rate     : {resus_first_8h:>8.1f} mL/h              |")
    if add_maintenance:
        print(f"  |    + maintenance (4-2-1) : {maint_hourly:>8.1f} mL/h              |")
        print(f"  |    = TOTAL first 8h rate : {total_first_8h_rate:>8.1f} mL/h              |")
    print(f"  |  Next 16h  (half)        : {r['next_16h_mL']:>8.1f} mL                |")
    print(f"  |    resuscitation rate     : {resus_next_16h:>8.1f} mL/h              |")
    if add_maintenance:
        print(f"  |    + maintenance (4-2-1) : {maint_hourly:>8.1f} mL/h              |")
        print(f"  |    = TOTAL next 16h rate : {total_next_16h_rate:>8.1f} mL/h              |")
    print("  +---------------------------------------------------------+")

    if add_maintenance:
        print()
        _print_421_breakdown(weight)

    print()
    print("  IMPORTANT: The 8h clock starts from TIME OF BURN,")
    print("  not time of admission. Adjust if fluid was already given.")

    # ---- Holliday-Segar maintenance (reference) ----
    hs = holliday_segar(weight)
    print()
    print("  Holliday-Segar Maintenance (reference):")
    if weight <= 10:
        rule = f"100 x {weight} kg"
    elif weight <= 20:
        rule = f"1000 + 50 x {weight - 10:.0f} kg (above 10 kg)"
    else:
        rule = f"1500 + 20 x {weight - 20:.0f} kg (above 20 kg)"
    print(f"    Formula : {rule}")
    print(f"    Daily   : {hs['daily_mL']:.1f} mL/day")
    print(f"    Hourly  : {hs['hourly_mL_per_h']:.2f} mL/h")

    if formula == "galveston":
        print()
        print("  Note: Galveston formula already includes maintenance.")
        print("  Holliday-Segar shown above for reference only.")

    # ---- Urine output target ----
    uo_min = 0.5 * weight
    uo_max = 1.0 * weight
    print()
    print(f"  Urine output target  : {uo_min:.1f}-{uo_max:.1f} mL/h  (0.5-1 mL/kg/h)")
    print(f"  Fluid type           : Lactated Ringer's (isotonic)")
    print()
    print("  Titrate infusion rate to urine output; above values are")
    print("  initial estimates only. Reassess hourly.")
    print("=" * 62)


def _print_421_breakdown(weight_kg: float) -> None:
    """Print the 4-2-1 maintenance calculation breakdown."""
    print("  4-2-1 Maintenance Breakdown:")
    if weight_kg <= 10:
        print(f"    4 x {weight_kg:.0f} kg = {4.0 * weight_kg:.0f} mL/h")
    elif weight_kg <= 20:
        extra = weight_kg - 10.0
        print(f"    4 x 10 kg                = 40 mL/h")
        print(f"    2 x {extra:.0f} kg (next 10 kg)  = {2.0 * extra:.0f} mL/h")
        print(f"    Total                    = {40.0 + 2.0 * extra:.0f} mL/h")
    else:
        extra = weight_kg - 20.0
        print(f"    4 x 10 kg                = 40 mL/h")
        print(f"    2 x 10 kg (next 10 kg)   = 20 mL/h")
        print(f"    1 x {extra:.0f} kg (above 20 kg) = {1.0 * extra:.0f} mL/h")
        print(f"    Total                    = {60.0 + 1.0 * extra:.0f} mL/h")


if __name__ == "__main__":
    main()
