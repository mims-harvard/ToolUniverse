"""General clinical fluid and dosing calculations.

Consolidates multiple calculation types into one script with --type subcommands.

Usage:
    # IV drip rate (replaces iv_drip_rate.py)
    python fluid_calculations.py --type drip_rate --volume_ml 50 --time_min 60 --drop_factor 60

    # Drug added to bag (additive or equal-volume replacement)
    python fluid_calculations.py --type drip_rate --drug_ml 4.7 --saline_ml 50 --time_min 60 --drop_factor 60
    python fluid_calculations.py --type drip_rate --drug_ml 4.7 --saline_ml 50 --time_min 60 --drop_factor 60 --replace_equal

    # BSA-based dose (e.g. chemotherapy)
    python fluid_calculations.py --type bsa_dose --dose_per_m2 25 --bsa 0.8
    python fluid_calculations.py --type bsa_dose --dose_per_m2 25 --bsa 0.8 --days 3

    # Maintenance fluids — Holliday-Segar (pediatric and adult)
    python fluid_calculations.py --type maintenance --weight_kg 22

    # Dilution — C1V1 = C2V2 (find any one unknown)
    python fluid_calculations.py --type dilution --c1 20 --v1 4.7 --v2 50
    python fluid_calculations.py --type dilution --c1 20 --v1 4.7 --c2 1.88
    python fluid_calculations.py --type dilution --c2 5 --v2 100 --v1 25

Supported --type values: drip_rate, bsa_dose, maintenance, dilution
"""

import argparse
import sys


# ---------------------------------------------------------------------------
# Calculation functions
# ---------------------------------------------------------------------------


def calc_drip_rate(
    volume_ml: float | None,
    drug_ml: float | None,
    saline_ml: float | None,
    time_min: float,
    drop_factor: float,
    replace_equal: bool = False,
) -> dict:
    """
    IV drip rate from total volume, infusion time, and drop factor.

    Returns mL/min, drops/min (exact and rounded).
    """
    if volume_ml is not None:
        total = volume_ml
        mix_note = f"Total volume: {volume_ml} mL"
    elif drug_ml is not None and saline_ml is not None:
        if replace_equal:
            total = saline_ml
            mix_note = (
                f"Equal-volume replacement: removed {drug_ml} mL saline, "
                f"added {drug_ml} mL drug → total stays {saline_ml} mL"
            )
        else:
            total = drug_ml + saline_ml
            mix_note = f"Additive: {drug_ml} mL drug + {saline_ml} mL saline = {total} mL"
    else:
        raise ValueError("Provide --volume_ml, or both --drug_ml and --saline_ml.")

    rate_ml_min = total / time_min
    drops_per_min = rate_ml_min * drop_factor
    return {
        "mix_note": mix_note,
        "total_volume_mL": total,
        "time_min": time_min,
        "drop_factor": drop_factor,
        "rate_mL_per_min": round(rate_ml_min, 4),
        "drops_per_min": round(drops_per_min, 2),
        "drops_per_min_rounded": round(drops_per_min),
        "rate_mL_per_h": round(rate_ml_min * 60, 2),
        "verification": f"{rate_ml_min:.4f} mL/min × {time_min} min = {rate_ml_min * time_min:.2f} mL  (should equal {total})",
    }


def calc_bsa_dose(
    dose_per_m2: float,
    bsa: float,
    days: int = 1,
) -> dict:
    """
    BSA-based dose (e.g. chemotherapy, targeted therapy).

    dose_per_m2: dose in any unit per m² per administration
    bsa: patient body surface area in m²
    days: number of days (course total; each day gets one administration at the per-day dose)
    """
    single_dose = dose_per_m2 * bsa
    total_course = single_dose * days
    return {
        "bsa_m2": bsa,
        "dose_per_m2": dose_per_m2,
        "single_dose": round(single_dose, 4),
        "days": days,
        "total_course_dose": round(total_course, 4),
        "verification": f"{dose_per_m2} × {bsa} m² = {single_dose:.4f} per day × {days} day(s) = {total_course:.4f} total",
    }


def calc_maintenance(weight_kg: float) -> dict:
    """
    Maintenance fluid requirements by two methods:

    Holliday-Segar (daily method):
        <= 10 kg : 100 mL/kg/day
        10-20 kg : 1000 + 50 mL/kg/day above 10 kg
        > 20 kg  : 1500 + 20 mL/kg/day above 20 kg

    4-2-1 rule (hourly method):
        First 10 kg  : 4 mL/kg/h
        Next 10 kg   : 2 mL/kg/h
        Each kg > 20 : 1 mL/kg/h
    """
    # Holliday-Segar (daily)
    if weight_kg <= 10:
        hs_daily = 100.0 * weight_kg
        hs_rule = f"100 x {weight_kg} kg"
    elif weight_kg <= 20:
        hs_daily = 1000.0 + 50.0 * (weight_kg - 10.0)
        hs_rule = f"1000 + 50 x {weight_kg - 10:.1f} kg (above 10 kg)"
    else:
        hs_daily = 1500.0 + 20.0 * (weight_kg - 20.0)
        hs_rule = f"1500 + 20 x {weight_kg - 20:.1f} kg (above 20 kg)"
    hs_hourly = hs_daily / 24.0

    # 4-2-1 rule (hourly)
    if weight_kg <= 10:
        rule421_hourly = 4.0 * weight_kg
        rule421_desc = f"4 x {weight_kg} kg"
    elif weight_kg <= 20:
        rule421_hourly = 40.0 + 2.0 * (weight_kg - 10.0)
        rule421_desc = f"4x10 + 2x{weight_kg - 10:.1f} kg"
    else:
        rule421_hourly = 60.0 + 1.0 * (weight_kg - 20.0)
        rule421_desc = f"4x10 + 2x10 + 1x{weight_kg - 20:.1f} kg"
    rule421_daily = rule421_hourly * 24.0

    return {
        "weight_kg": weight_kg,
        "holliday_segar": {
            "formula": "Holliday-Segar",
            "rule_applied": hs_rule,
            "daily_mL": round(hs_daily, 1),
            "hourly_mL_per_h": round(hs_hourly, 2),
        },
        "four_two_one": {
            "formula": "4-2-1 rule",
            "rule_applied": rule421_desc,
            "hourly_mL_per_h": round(rule421_hourly, 2),
            "daily_mL": round(rule421_daily, 1),
        },
        "verification": (
            f"Holliday-Segar: {hs_rule} = {hs_daily:.1f} mL/day = {hs_hourly:.2f} mL/h | "
            f"4-2-1: {rule421_desc} = {rule421_hourly:.2f} mL/h = {rule421_daily:.1f} mL/day"
        ),
    }


def calc_dilution(
    c1: float | None = None,
    v1: float | None = None,
    c2: float | None = None,
    v2: float | None = None,
) -> dict:
    """
    C1·V1 = C2·V2 dilution equation.
    Provide exactly three values; the fourth is calculated.
    Units are arbitrary but must be consistent (same concentration unit, same volume unit).
    """
    knowns = {"c1": c1, "v1": v1, "c2": c2, "v2": v2}
    unknowns = [k for k, v in knowns.items() if v is None]
    if len(unknowns) != 1:
        raise ValueError(f"Provide exactly 3 of c1, v1, c2, v2 (got {4 - len(unknowns)} known values).")

    target = unknowns[0]
    if target == "c1":
        val = (c2 * v2) / v1  # type: ignore[operator]
    elif target == "v1":
        val = (c2 * v2) / c1  # type: ignore[operator]
    elif target == "c2":
        val = (c1 * v1) / v2  # type: ignore[operator]
    else:  # v2
        val = (c1 * v1) / c2  # type: ignore[operator]

    result = dict(c1=c1, v1=v1, c2=c2, v2=v2)
    result[target] = round(val, 6)

    verification_lhs = result["c1"] * result["v1"]  # type: ignore[operator]
    verification_rhs = result["c2"] * result["v2"]  # type: ignore[operator]
    return {
        **result,
        "solved_for": target,
        "solved_value": round(val, 6),
        "verification": f"C1·V1 = {verification_lhs:.4f}  |  C2·V2 = {verification_rhs:.4f}  (should be equal)",
    }


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


def _print_drip_rate(r: dict) -> None:
    print("=" * 60)
    print("  IV Drip Rate")
    print("=" * 60)
    print(f"  {r['mix_note']}")
    print(f"  Infusion time   : {r['time_min']} min")
    print(f"  Drop factor     : {r['drop_factor']} drops/mL")
    print()
    print(f"  ┌─────────────────────────────────────────┐")
    print(f"  │  Rate          : {r['rate_mL_per_min']:.4f} mL/min           │")
    print(f"  │  Rate          : {r['rate_mL_per_h']:.2f} mL/h              │")
    print(f"  │  Drip rate     : {r['drops_per_min']:.1f} drops/min          │")
    print(f"  │  Drip rate     : {r['drops_per_min_rounded']} drops/min (rounded)    │")
    print(f"  └─────────────────────────────────────────┘")
    print()
    print(f"  Verification: {r['verification']}")
    print("=" * 60)


def _print_bsa_dose(r: dict) -> None:
    print("=" * 60)
    print("  BSA-Based Dose")
    print("=" * 60)
    print(f"  BSA             : {r['bsa_m2']} m²")
    print(f"  Dose per m²     : {r['dose_per_m2']} (units as given)")
    print()
    print(f"  ┌─────────────────────────────────────────┐")
    print(f"  │  Single dose   : {r['single_dose']:.4f}                  │")
    if r["days"] > 1:
        print(f"  │  Course days   : {r['days']}                          │")
        print(f"  │  Total course  : {r['total_course_dose']:.4f}                  │")
    print(f"  └─────────────────────────────────────────┘")
    print()
    print(f"  Verification: {r['verification']}")
    print("=" * 60)


def _print_maintenance(r: dict) -> None:
    hs = r["holliday_segar"]
    f21 = r["four_two_one"]
    print("=" * 60)
    print("  Maintenance Fluids")
    print("=" * 60)
    print(f"  Weight          : {r['weight_kg']} kg")
    print()
    print("  Holliday-Segar (daily method):")
    print(f"    Rule          : {hs['rule_applied']}")
    print(f"    Daily         : {hs['daily_mL']:.1f} mL/day")
    print(f"    Hourly        : {hs['hourly_mL_per_h']:.2f} mL/h")
    print()
    print("  4-2-1 Rule (hourly method):")
    print(f"    Rule          : {f21['rule_applied']}")
    print(f"    Hourly        : {f21['hourly_mL_per_h']:.2f} mL/h")
    print(f"    Daily equiv.  : {f21['daily_mL']:.1f} mL/day")
    print()
    print(f"  Verification: {r['verification']}")
    print("=" * 60)


def _print_dilution(r: dict) -> None:
    print("=" * 60)
    print("  Dilution — C1·V1 = C2·V2")
    print("=" * 60)
    print(f"  C1 = {r['c1']}   V1 = {r['v1']}")
    print(f"  C2 = {r['c2']}   V2 = {r['v2']}")
    print()
    print(f"  ┌─────────────────────────────────────────┐")
    print(f"  │  {r['solved_for'].upper()} = {r['solved_value']:<35}│")
    print(f"  └─────────────────────────────────────────┘")
    print()
    print(f"  Verification: {r['verification']}")
    print("=" * 60)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Clinical fluid and dosing calculator.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--type",
        required=True,
        choices=["drip_rate", "bsa_dose", "maintenance", "dilution"],
        help="Calculation type.",
    )

    # drip_rate parameters
    parser.add_argument("--volume_ml", type=float, help="[drip_rate] Total infusion volume (mL).")
    parser.add_argument("--drug_ml", type=float, help="[drip_rate] Drug solution volume added to bag (mL).")
    parser.add_argument("--saline_ml", type=float, help="[drip_rate] Saline bag volume (mL).")
    parser.add_argument("--time_min", type=float, help="[drip_rate] Infusion time (minutes).")
    parser.add_argument("--drop_factor", type=float, help="[drip_rate] Drop factor (drops/mL).")
    parser.add_argument(
        "--replace_equal",
        action="store_true",
        help="[drip_rate] Equal-volume replacement: remove drug_ml of saline before adding drug.",
    )

    # bsa_dose parameters
    parser.add_argument("--dose_per_m2", type=float, help="[bsa_dose] Dose per m² per administration.")
    parser.add_argument("--bsa", type=float, help="[bsa_dose] Patient BSA (m²).")
    parser.add_argument("--days", type=int, default=1, help="[bsa_dose] Number of administration days (default 1).")

    # maintenance parameters
    parser.add_argument("--weight_kg", type=float, help="[maintenance] Patient weight (kg).")

    # dilution parameters
    parser.add_argument("--c1", type=float, default=None, help="[dilution] Initial concentration.")
    parser.add_argument("--v1", type=float, default=None, help="[dilution] Initial volume.")
    parser.add_argument("--c2", type=float, default=None, help="[dilution] Final concentration.")
    parser.add_argument("--v2", type=float, default=None, help="[dilution] Final volume.")

    args = parser.parse_args()

    try:
        if args.type == "drip_rate":
            if args.time_min is None or args.drop_factor is None:
                parser.error("drip_rate requires --time_min and --drop_factor.")
            result = calc_drip_rate(
                args.volume_ml, args.drug_ml, args.saline_ml,
                args.time_min, args.drop_factor, args.replace_equal,
            )
            _print_drip_rate(result)

        elif args.type == "bsa_dose":
            if args.dose_per_m2 is None or args.bsa is None:
                parser.error("bsa_dose requires --dose_per_m2 and --bsa.")
            if args.bsa <= 0:
                parser.error("--bsa must be positive.")
            result = calc_bsa_dose(args.dose_per_m2, args.bsa, args.days)
            _print_bsa_dose(result)

        elif args.type == "maintenance":
            if args.weight_kg is None:
                parser.error("maintenance requires --weight_kg.")
            if args.weight_kg <= 0:
                parser.error("--weight_kg must be positive.")
            result = calc_maintenance(args.weight_kg)
            _print_maintenance(result)

        elif args.type == "dilution":
            result = calc_dilution(args.c1, args.v1, args.c2, args.v2)
            _print_dilution(result)

    except ValueError as exc:
        print(f"Error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
