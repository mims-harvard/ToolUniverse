#!/usr/bin/env python3
"""Generate or validate an nf-core samplesheet for rnaseq / sarek / atacseq.

Discovers FASTQ files under a directory, pairs R1/R2 by filename pattern,
infers a sample name per pair, and writes the pipeline-specific CSV format.
Never invents metadata it cannot infer (strandedness is left as 'auto' for
rnaseq; sarek tumor/normal status is asked about explicitly rather than
guessed when it cannot be inferred from filenames).
"""

import argparse
import csv
import re
import sys
from pathlib import Path

FASTQ_RE = re.compile(r"\.(fastq|fq)\.gz$", re.IGNORECASE)

# R1/R2 markers commonly used by sequencers / SRA fasterq-dump output.
R1_PATTERNS = [r"_R1[_.]", r"_R1$", r"_1\.fastq", r"_1\.fq"]
R2_PATTERNS = [r"_R2[_.]", r"_R2$", r"_2\.fastq", r"_2\.fq"]

PIPELINE_COLUMNS = {
    "rnaseq": ["sample", "fastq_1", "fastq_2", "strandedness"],
    "sarek": ["patient", "sample", "lane", "fastq_1", "fastq_2", "status"],
    "atacseq": ["sample", "fastq_1", "fastq_2", "replicate"],
}


def find_read_number(name):
    for pat in R1_PATTERNS:
        if re.search(pat, name):
            return 1
    for pat in R2_PATTERNS:
        if re.search(pat, name):
            return 2
    return None


def sample_name_from_file(path, read_num):
    """Strip the R1/R2 marker (and .fastq.gz) to get a sample base name."""
    name = path.name
    name = FASTQ_RE.sub("", name)
    for pat in R1_PATTERNS + R2_PATTERNS:
        name = re.sub(pat.rstrip("$"), "", name)
        name = re.sub(pat, "", name)
    name = name.strip("_.-")
    return name or path.stem


def discover_pairs(data_dir):
    """Return list of dicts: {sample, r1, r2 (or None), tumor_hint}."""
    files = sorted(p for p in Path(data_dir).rglob("*") if FASTQ_RE.search(p.name))
    if not files:
        return []

    by_sample = {}
    unpaired = []
    for f in files:
        rn = find_read_number(f.name)
        if rn is None:
            unpaired.append(f)
            continue
        sample = sample_name_from_file(f, rn)
        entry = by_sample.setdefault(sample, {"sample": sample, "r1": None, "r2": None})
        if rn == 1:
            entry["r1"] = str(f.resolve())
        else:
            entry["r2"] = str(f.resolve())

    pairs = list(by_sample.values())
    for f in unpaired:
        # Single-end file with no R1/R2 marker at all.
        sample = FASTQ_RE.sub("", f.name).strip("_.-") or f.stem
        pairs.append({"sample": sample, "r1": str(f.resolve()), "r2": None})

    return sorted(pairs, key=lambda d: d["sample"])


def infer_status(sample_name):
    """Best-effort tumor/normal status for sarek: 1=tumor, 0=normal, None=unknown."""
    lname = sample_name.lower()
    if "tumor" in lname or "tumour" in lname:
        return 1
    if "normal" in lname:
        return 0
    return None


def write_rnaseq(pairs, out_path):
    with open(out_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(PIPELINE_COLUMNS["rnaseq"])
        for p in pairs:
            w.writerow([p["sample"], p["r1"], p["r2"] or "", "auto"])


def write_atacseq(pairs, out_path):
    with open(out_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(PIPELINE_COLUMNS["atacseq"])
        # replicate number per unique sample-without-replicate-suffix, defaulting to 1
        seen = {}
        for p in pairs:
            seen[p["sample"]] = seen.get(p["sample"], 0) + 1
            w.writerow([p["sample"], p["r1"], p["r2"] or "", seen[p["sample"]]])


def write_sarek(pairs, out_path, interactive):
    rows = []
    unresolved = []
    for p in pairs:
        status = infer_status(p["sample"])
        if status is None:
            unresolved.append(p["sample"])
            status = 0  # placeholder; flagged below
        rows.append(
            {
                "patient": p["sample"],
                "sample": p["sample"],
                "lane": "L001",
                "fastq_1": p["r1"],
                "fastq_2": p["r2"] or "",
                "status": status,
            }
        )
    with open(out_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(PIPELINE_COLUMNS["sarek"])
        for r in rows:
            w.writerow([r[c] for c in PIPELINE_COLUMNS["sarek"]])

    if unresolved:
        print(
            "WARNING: could not infer tumor(1)/normal(0) status from filename for: "
            + ", ".join(unresolved)
            + ". Defaulted to status=0 (normal) in the samplesheet -- "
            "EDIT THESE MANUALLY before running sarek. Filenames containing "
            "'tumor'/'tumour' or 'normal' are auto-detected; nothing else is guessed.",
            file=sys.stderr,
        )


def generate(data_dir, pipeline, out_path):
    pairs = discover_pairs(data_dir)
    if not pairs:
        print(f"No FASTQ (.fastq.gz/.fq.gz) files found under {data_dir}", file=sys.stderr)
        return 1

    if pipeline == "rnaseq":
        write_rnaseq(pairs, out_path)
    elif pipeline == "atacseq":
        write_atacseq(pairs, out_path)
    elif pipeline == "sarek":
        write_sarek(pairs, out_path, interactive=False)
    else:
        print(f"Unknown pipeline: {pipeline}", file=sys.stderr)
        return 1

    print(f"Wrote {len(pairs)} sample row(s) to {out_path} (pipeline={pipeline})")
    for p in pairs:
        pairing = "paired" if p["r2"] else "single-end"
        print(f"  - {p['sample']}: {pairing}")
    return 0


def validate(samplesheet_path, pipeline):
    expected = PIPELINE_COLUMNS.get(pipeline)
    if not expected:
        print(f"Unknown pipeline: {pipeline}", file=sys.stderr)
        return 1

    with open(samplesheet_path, newline="") as fh:
        reader = csv.DictReader(fh)
        header = reader.fieldnames or []
        rows = list(reader)

    ok = True
    missing = [c for c in expected if c not in header]
    extra = [c for c in header if c not in expected]
    if missing:
        print(f"FAIL: missing required column(s): {missing}")
        ok = False
    if extra:
        print(f"WARN: unexpected extra column(s) (not necessarily an error): {extra}")

    if not rows:
        print("FAIL: samplesheet has no data rows")
        ok = False

    for i, row in enumerate(rows, start=2):  # row 1 is the header
        fq1 = row.get("fastq_1", "")
        fq2 = row.get("fastq_2", "")
        if fq1 and not Path(fq1).exists():
            print(f"FAIL: row {i}: fastq_1 does not exist on disk: {fq1}")
            ok = False
        if fq2 and not Path(fq2).exists():
            print(f"FAIL: row {i}: fastq_2 does not exist on disk: {fq2}")
            ok = False
        if pipeline == "sarek" and row.get("status") not in ("0", "1"):
            print(f"FAIL: row {i}: sarek 'status' must be 0 (normal) or 1 (tumor), "
                  f"got {row.get('status')!r}")
            ok = False

    print("VALID" if ok else "INVALID")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("data_dir_or_flag", help="Directory of FASTQs (generate mode), or samplesheet path (--validate mode)")
    ap.add_argument("pipeline_or_sheet", help="pipeline name: rnaseq|sarek|atacseq")
    ap.add_argument("--validate", action="store_true", help="Validate an existing samplesheet instead of generating one")
    ap.add_argument("-o", "--output", default="samplesheet.csv", help="Output CSV path (generate mode)")
    args = ap.parse_args()

    if args.validate:
        # usage: generate_samplesheet.py --validate samplesheet.csv <pipeline>
        sheet = args.data_dir_or_flag
        pipeline = args.pipeline_or_sheet
        if not pipeline:
            print("Usage: generate_samplesheet.py --validate <samplesheet.csv> <pipeline>", file=sys.stderr)
            return 2
        return validate(sheet, pipeline)

    data_dir = args.data_dir_or_flag
    pipeline = args.pipeline_or_sheet
    if pipeline not in PIPELINE_COLUMNS:
        print(f"Usage: generate_samplesheet.py <data_dir> <{'|'.join(PIPELINE_COLUMNS)}> [-o out.csv]", file=sys.stderr)
        return 2
    return generate(data_dir, pipeline, args.output)


if __name__ == "__main__":
    sys.exit(main())
