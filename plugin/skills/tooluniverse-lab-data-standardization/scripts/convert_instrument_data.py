#!/usr/bin/env python3
"""Convert a lab instrument output file (CSV/TSV/XLSX/PDF) into an
Allotrope-Simple-Model-INSPIRED JSON document, plus an optional flattened
2D CSV.

Two-tier strategy:
  Tier 1 (native): uses the real `allotropy` library if it is installed and
      recognizes the file's instrument vendor. Produces a genuine ASM
      document (tier="native").
  Tier 2 (fallback): a generic tabular parser built only on ToolUniverse's
      existing dependencies (pandas / openpyxl / pdfplumber). Produces a
      best-effort ASM-like document (tier="fallback") and says so.

Honesty contract: this script never invents a value that is not present in
the source file. If it cannot classify or parse something, it leaves it out
(or flags it) rather than guessing.
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path

RAW_HINTS = re.compile(
    r"(abs(orbance)?|^od\b|od\d|fluor|intensity|\bct\b|\bcq\b|count|area|height|signal|^raw)",
    re.IGNORECASE,
)
CALC_HINTS = re.compile(
    r"(conc(entration)?|%|percent|ratio|\bcv\b|fold|\brq\b|delta|normali[sz]ed|"
    r"corrected|purity|viability|\bdin\b|\brin\b)",
    re.IGNORECASE,
)
ID_HINTS = re.compile(r"(sample|well|specimen|tube)[\s_-]?(id|name|position|location)?", re.IGNORECASE)


def try_import_allotropy():
    try:
        import allotropy  # noqa: F401
        from allotropy.parser_factory import Vendor  # noqa: F401

        return allotropy
    except ImportError:
        return None


def install_plan_message():
    return (
        "allotropy is not installed — Tier 1 (native, vendor-certified ASM "
        "parsing) is unavailable.\n"
        "  Install it with:  pip install allotropy\n"
        "Falling back to Tier 2 (generic tabular parser). Tier 2 output is "
        "structurally similar but NOT a certified ASM conversion — it is "
        "tagged tier='fallback' in the output JSON."
    )


def load_table(input_path: Path, sheet=None):
    """Load a CSV/TSV/XLSX/PDF file into a list of dict rows + header list.
    Returns (headers, rows). Raises ValueError with a clear message on
    unsupported/unparseable input — never fabricates rows.
    """
    suffix = input_path.suffix.lower()

    if suffix in (".csv", ".tsv", ".txt"):
        delimiter = "\t" if suffix == ".tsv" else None
        with open(input_path, newline="", encoding="utf-8-sig") as f:
            sample = f.read(4096)
            f.seek(0)
            if delimiter is None:
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
                    delimiter = dialect.delimiter
                except csv.Error:
                    delimiter = ","
            reader = csv.DictReader(f, delimiter=delimiter)
            rows = [dict(r) for r in reader]
            headers = reader.fieldnames or []
        if not headers:
            raise ValueError(f"No header row detected in {input_path}")
        return headers, rows

    if suffix in (".xlsx", ".xls"):
        try:
            import pandas as pd
        except ImportError:
            raise ValueError(
                "pandas is required to read Excel files but is not importable "
                "in this environment (it is a declared ToolUniverse dependency "
                "— check your environment/venv)."
            )
        df = pd.read_excel(input_path, sheet_name=sheet or 0)
        headers = [str(c) for c in df.columns]
        rows = df.astype(object).where(df.notnull(), None).to_dict(orient="records")
        rows = [{str(k): v for k, v in r.items()} for r in rows]
        return headers, rows

    if suffix == ".pdf":
        try:
            import pdfplumber
        except ImportError:
            raise ValueError(
                "pdfplumber is required to read PDF tables but is not "
                "importable in this environment (it is a declared "
                "ToolUniverse dependency — check your environment/venv)."
            )
        with pdfplumber.open(input_path) as pdf:
            for page in pdf.pages:
                table = page.extract_table()
                if table and len(table) > 1:
                    headers = [str(c) if c is not None else "" for c in table[0]]
                    rows = [dict(zip(headers, row)) for row in table[1:]]
                    return headers, rows
        raise ValueError(
            f"No extractable table found in {input_path}. If this is a "
            "scanned image PDF, no OCR is bundled in this skill — export "
            "the instrument data as CSV/XLSX instead."
        )

    raise ValueError(
        f"Unsupported file type '{suffix}'. Supported: .csv, .tsv, .xlsx, .pdf"
    )


def classify_columns(headers):
    id_cols, well_cols, raw_cols, calc_cols, unclassified = [], [], [], [], []
    for h in headers:
        hl = h.strip()
        if not hl:
            continue
        if re.search(r"well", hl, re.IGNORECASE):
            well_cols.append(h)
        elif ID_HINTS.search(hl):
            id_cols.append(h)
        elif CALC_HINTS.search(hl):
            calc_cols.append(h)
        elif RAW_HINTS.search(hl):
            raw_cols.append(h)
        else:
            unclassified.append(h)
    return id_cols, well_cols, raw_cols, calc_cols, unclassified


def to_number(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return v
    s = str(v).strip()
    if s == "" or s.lower() in ("na", "n/a", "nan", "none"):
        return None
    try:
        return int(s)
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return None


def fallback_convert(input_path: Path, sheet=None):
    headers, rows = load_table(input_path, sheet=sheet)
    id_cols, well_cols, raw_cols, calc_cols, unclassified = classify_columns(headers)
    # Unclassified numeric-looking columns default to raw (safer: no
    # traceability claim is made for them).
    numeric_unclassified = []
    for h in unclassified:
        if rows and any(to_number(r.get(h)) is not None for r in rows):
            numeric_unclassified.append(h)
    raw_cols = raw_cols + numeric_unclassified

    measurement_docs = []
    calc_docs = []
    for i, row in enumerate(rows, start=1):
        meas_id = f"M{i:04d}"
        sample_id = None
        for c in id_cols:
            if row.get(c):
                sample_id = row[c]
                break
        well = None
        for c in well_cols:
            if row.get(c):
                well = row[c]
                break

        raw_measurements = {}
        for c in raw_cols:
            val = to_number(row.get(c))
            if val is not None:
                raw_measurements[c] = {"value": val, "unit": None}

        measurement_docs.append(
            {
                "measurement_identifier": meas_id,
                "sample_document": {
                    "sample_identifier": sample_id,
                    "well_location_identifier": well,
                },
                "raw_measurements": raw_measurements,
                "measurement_time": None,
            }
        )

        for j, c in enumerate(calc_cols, start=1):
            val = to_number(row.get(c))
            if val is None:
                continue
            # Traceability: link to this row's measurement + the first raw
            # column present, since the fallback parser has no way to know
            # the true formula. If there is no raw column to point at, do
            # NOT emit the calculated value at all (avoids an untraceable
            # "calculated" claim).
            if not raw_measurements:
                continue
            source_feature = next(iter(raw_measurements))
            calc_docs.append(
                {
                    "calculated_data_identifier": f"C{i:04d}_{j:02d}",
                    "calculated_data_name": c,
                    "calculated_result": {"value": val, "unit": None},
                    "data_source_aggregate_document": {
                        "data_source_document": [
                            {
                                "data_source_identifier": meas_id,
                                "data_source_feature": source_feature,
                            }
                        ]
                    },
                }
            )

    doc = {
        "asm_like": True,
        "tier": "fallback",
        "note": "not ASM-validated, best-effort structural parse",
        "source_file": str(input_path.name),
        "detected_instrument": "generic-tabular",
        "device_system_document": {
            "device_identifier": None,
            "model_number": None,
            "asset_management_identifier": None,
        },
        "measurement_documents": measurement_docs,
        "calculated_data_aggregate_document": {"calculated_data_document": calc_docs},
    }
    return doc


def native_convert(input_path: Path, vendor_name: str):
    from allotropy.parser_factory import Vendor
    from allotropy.to_allotrope import allotrope_from_file

    vendor = Vendor[vendor_name]
    asm = allotrope_from_file(str(input_path), vendor)
    return {
        "asm_like": True,
        "tier": "native",
        "source_file": str(input_path.name),
        "detected_instrument": vendor_name,
        "allotropy_document": asm,
    }


def flatten(doc: dict):
    """Flatten a produced JSON document into rows for a 2D CSV."""
    rows = []
    calc_by_source = {}
    for c in doc.get("calculated_data_aggregate_document", {}).get(
        "calculated_data_document", []
    ):
        for src in c.get("data_source_aggregate_document", {}).get(
            "data_source_document", []
        ):
            calc_by_source.setdefault(src["data_source_identifier"], []).append(c)

    for m in doc.get("measurement_documents", []):
        base = {
            "measurement_identifier": m["measurement_identifier"],
            "sample_identifier": m.get("sample_document", {}).get("sample_identifier"),
            "well_location_identifier": m.get("sample_document", {}).get(
                "well_location_identifier"
            ),
        }
        for name, v in m.get("raw_measurements", {}).items():
            row = dict(base)
            row["field"] = name
            row["value"] = v.get("value")
            row["unit"] = v.get("unit")
            row["kind"] = "raw"
            rows.append(row)
        for c in calc_by_source.get(m["measurement_identifier"], []):
            row = dict(base)
            row["field"] = c["calculated_data_name"]
            row["value"] = c["calculated_result"].get("value")
            row["unit"] = c["calculated_result"].get("unit")
            row["kind"] = "calculated"
            rows.append(row)
    return rows


def write_csv(rows, out_path: Path):
    if not rows:
        with open(out_path, "w") as f:
            f.write("")
        return
    fieldnames = list(rows[0].keys())
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", type=Path, help="Instrument output file (.csv/.tsv/.xlsx/.pdf)")
    ap.add_argument("--output-dir", type=Path, default=None, help="Output directory (default: <input_dir>/<stem>_asm_results)")
    ap.add_argument("--sheet", default=None, help="Excel sheet name/index (xlsx only)")
    ap.add_argument("--vendor", default=None, help="Force a specific allotropy Vendor name (Tier 1)")
    ap.add_argument("--force-fallback", action="store_true", help="Skip Tier 1 even if allotropy is installed")
    ap.add_argument("--format", choices=["json", "csv", "both"], default="both")
    args = ap.parse_args()

    input_path = args.input
    if not input_path.exists():
        print(f"ERROR: input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    out_dir = args.output_dir or input_path.parent / f"{input_path.stem}_asm_results"
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = None
    if not args.force_fallback and args.vendor:
        allotropy_mod = try_import_allotropy()
        if allotropy_mod is None:
            print(install_plan_message())
        else:
            try:
                doc = native_convert(input_path, args.vendor)
                print(f"Tier 1 (native allotropy, vendor={args.vendor}) conversion succeeded.")
            except Exception as e:
                print(f"Tier 1 native conversion failed ({e}); falling back to Tier 2.")
                doc = None
    elif not args.force_fallback:
        allotropy_mod = try_import_allotropy()
        if allotropy_mod is None:
            print(install_plan_message())

    if doc is None:
        try:
            doc = fallback_convert(input_path, sheet=args.sheet)
        except ValueError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)
        n_meas = len(doc["measurement_documents"])
        n_calc = len(doc["calculated_data_aggregate_document"]["calculated_data_document"])
        print(f"Tier 2 (fallback) conversion done: {n_meas} measurement(s), {n_calc} calculated value(s).")
        if n_meas == 0:
            print(
                "WARNING: 0 measurements were extracted — this usually means the "
                "file has no delimited header/data rows the parser could "
                "recognize (e.g. free text, or a single-column file). No values "
                "were fabricated to fill this in; check the source file.",
                file=sys.stderr,
            )

    json_path = out_dir / f"{input_path.stem}_asm.json"
    csv_path = out_dir / f"{input_path.stem}_flat.csv"

    if args.format in ("json", "both"):
        with open(json_path, "w") as f:
            json.dump(doc, f, indent=2, default=str)
        print(f"Wrote {json_path}")

    if args.format in ("csv", "both") and doc.get("tier") != "native":
        rows = flatten(doc)
        write_csv(rows, csv_path)
        print(f"Wrote {csv_path} ({len(rows)} row(s))")
    elif args.format in ("csv", "both"):
        print("Flattened CSV is only implemented for tier='fallback' documents in this script; use flatten_to_csv.py's allotropy-aware path for native output.")


if __name__ == "__main__":
    main()
