#!/usr/bin/env python3
"""Flatten a JSON document produced by convert_instrument_data.py into a
2D CSV (one row per raw or calculated value). Standalone entry point for
when you already have the JSON and just want the CSV regenerated or
re-derived with a different output path — the same flatten() logic used
inline by convert_instrument_data.py.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from convert_instrument_data import flatten, write_csv  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input_json", type=Path, help="ASM-like JSON produced by convert_instrument_data.py")
    ap.add_argument("-o", "--output", type=Path, default=None, help="Output CSV path (default: <input>_flat.csv)")
    args = ap.parse_args()

    if not args.input_json.exists():
        print(f"ERROR: {args.input_json} not found", file=sys.stderr)
        sys.exit(1)

    with open(args.input_json) as f:
        doc = json.load(f)

    if doc.get("tier") == "native":
        print(
            "ERROR: this JSON is a Tier 1 (native allotropy) document — its "
            "internal structure is allotropy's own ASM schema, not the "
            "fallback shape this flattener understands. Use allotropy's own "
            "flattening utilities for native documents.",
            file=sys.stderr,
        )
        sys.exit(1)

    rows = flatten(doc)
    out_path = args.output or args.input_json.with_name(args.input_json.stem.replace("_asm", "") + "_flat.csv")
    write_csv(rows, out_path)
    print(f"Wrote {out_path} ({len(rows)} row(s))")


if __name__ == "__main__":
    main()
