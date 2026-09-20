#!/usr/bin/env python3
"""Structurally validate a JSON document produced by convert_instrument_data.py.

Soft validation by default: unknown/unexpected fields are WARNINGS, not
errors (forward-compatible). Use --strict to treat warnings as errors.

Exit codes: 0 = pass (no errors), 1 = fail (errors present, or --strict
with warnings present), 2 = could not even parse the file.
"""

import argparse
import json
import sys
from pathlib import Path


def validate(doc: dict):
    errors = []
    warnings = []

    for required in ("asm_like", "tier", "source_file", "measurement_documents"):
        if required not in doc:
            errors.append(f"missing required top-level field: '{required}'")

    tier = doc.get("tier")
    if tier not in ("native", "fallback"):
        warnings.append(f"unrecognized tier value: {tier!r} (expected 'native' or 'fallback')")
    if tier == "fallback" and "note" not in doc:
        warnings.append("tier='fallback' document is missing the explanatory 'note' field")

    measurements = doc.get("measurement_documents", [])
    if not isinstance(measurements, list):
        errors.append("'measurement_documents' must be a list")
        measurements = []
    if len(measurements) == 0:
        warnings.append("'measurement_documents' is empty — no measurements were extracted")

    seen_ids = set()
    for i, m in enumerate(measurements):
        mid = m.get("measurement_identifier")
        if not mid:
            errors.append(f"measurement_documents[{i}] missing 'measurement_identifier'")
        elif mid in seen_ids:
            errors.append(f"duplicate measurement_identifier: {mid}")
        else:
            seen_ids.add(mid)

        raw = m.get("raw_measurements", {})
        if not isinstance(raw, dict):
            errors.append(f"measurement_documents[{i}].raw_measurements must be a dict")
            continue
        for field, v in raw.items():
            if not isinstance(v, dict) or "value" not in v:
                errors.append(
                    f"measurement_documents[{i}].raw_measurements['{field}'] "
                    "must be an object with a 'value' key"
                )
                continue
            val = v["value"]
            if val is not None and not isinstance(val, (int, float)):
                errors.append(
                    f"measurement_documents[{i}].raw_measurements['{field}'].value "
                    f"is not numeric: {val!r}"
                )
            if v.get("unit") is None:
                warnings.append(
                    f"measurement_documents[{i}].raw_measurements['{field}'] has no unit"
                )

    calc_docs = doc.get("calculated_data_aggregate_document", {}).get(
        "calculated_data_document", []
    )
    for i, c in enumerate(calc_docs):
        if "calculated_result" not in c or "value" not in c.get("calculated_result", {}):
            errors.append(f"calculated_data_document[{i}] missing calculated_result.value")
        src = c.get("data_source_aggregate_document", {}).get("data_source_document", [])
        if not src:
            errors.append(
                f"calculated_data_document[{i}] ('{c.get('calculated_data_name')}') "
                "has no data_source_aggregate_document — calculated values MUST be "
                "traceable to the raw measurement they were derived from"
            )
        else:
            for s in src:
                ref = s.get("data_source_identifier")
                if ref not in seen_ids:
                    errors.append(
                        f"calculated_data_document[{i}] references unknown "
                        f"data_source_identifier '{ref}'"
                    )

    return errors, warnings


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input_json", type=Path)
    ap.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    args = ap.parse_args()

    if not args.input_json.exists():
        print(f"ERROR: {args.input_json} not found", file=sys.stderr)
        sys.exit(2)

    try:
        with open(args.input_json) as f:
            doc = json.load(f)
    except json.JSONDecodeError as e:
        print(f"FAIL: not valid JSON: {e}")
        sys.exit(2)

    errors, warnings = validate(doc)

    for w in warnings:
        print(f"WARN: {w}")
    for e in errors:
        print(f"ERROR: {e}")

    if errors:
        print(f"\nFAIL — {len(errors)} error(s), {len(warnings)} warning(s)")
        sys.exit(1)
    if warnings and args.strict:
        print(f"\nFAIL (--strict) — 0 errors, {len(warnings)} warning(s) treated as errors")
        sys.exit(1)
    print(f"\nPASS — 0 errors, {len(warnings)} warning(s)")
    sys.exit(0)


if __name__ == "__main__":
    main()
