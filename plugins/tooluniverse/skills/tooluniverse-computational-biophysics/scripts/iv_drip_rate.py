#!/usr/bin/env python3
"""Calculate IV drip rate from infusion parameters.
Usage: python iv_drip_rate.py --volume_ml 50 --time_min 60 --drop_factor 60
       python iv_drip_rate.py --drug_ml 4.7 --saline_ml 50 --time_min 60 --drop_factor 60
"""
import argparse

def main():
    parser = argparse.ArgumentParser(description="IV drip rate calculator")
    parser.add_argument('--volume_ml', type=float, help='Total volume to infuse (mL)')
    parser.add_argument('--drug_ml', type=float, help='Volume of drug solution added (mL)')
    parser.add_argument('--saline_ml', type=float, help='Volume of saline bag (mL)')
    parser.add_argument('--time_min', type=float, required=True, help='Infusion time (minutes)')
    parser.add_argument('--drop_factor', type=float, required=True, help='Drop factor (drops/mL)')
    parser.add_argument('--replace_equal', action='store_true',
                        help='In clinical practice, remove equal volume of saline before adding drug')
    args = parser.parse_args()

    if args.volume_ml:
        total = args.volume_ml
    elif args.drug_ml and args.saline_ml:
        if args.replace_equal:
            # Clinical practice: remove drug_ml of saline, then add drug_ml of drug
            # Total volume stays at saline_ml
            total = args.saline_ml
            print(f"Equal-volume replacement: removed {args.drug_ml} mL saline, added {args.drug_ml} mL drug")
            print(f"Total volume = {args.saline_ml} mL (unchanged)")
        else:
            total = args.drug_ml + args.saline_ml
            print(f"Additive: {args.drug_ml} mL drug + {args.saline_ml} mL saline = {total} mL total")
    else:
        print("Provide either --volume_ml or both --drug_ml and --saline_ml")
        return

    rate_ml_min = total / args.time_min
    drops_per_min = rate_ml_min * args.drop_factor

    print(f"\nRate: {rate_ml_min:.4f} mL/min")
    print(f"Drip rate: {drops_per_min:.1f} drops/min")
    print(f"Rounded: {round(drops_per_min)} drops/min")

if __name__ == '__main__':
    main()
