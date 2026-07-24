#!/usr/bin/env python3
"""Per-sample coding-variant counting with intronic/intergenic/UTR filtering.

Solves the recurring "average X variants per sample after filtering out
intronic, intergenic, and UTR variants" question pattern. Two filters are
applied in canonical order, mirroring the standard exome-trio analysis
workflow:

  1. Drop reference calls. Many clinical variant exports include a
     ``Zygosity`` column that flags rows where the called genotype matches
     the reference (these blow up per-sample counts ~10x). If a Zygosity
     column is present, rows with ``Zygosity == "Reference"`` are removed.
     Suppress with ``--no-zygosity-filter`` if your input doesn't have
     a Zygosity column or if reference calls have already been removed.

  2. Drop non-coding annotations. Records whose Sequence Ontology
     (Combined) value is in
     ``{intron_variant, intergenic_variant, 3_prime_UTR_variant,
        5_prime_UTR_variant, upstream_gene_variant,
        downstream_gene_variant}``
     are excluded. The default exclude set matches the canonical
     "exclude intronic, intergenic, and UTR" filter wording — pass
     ``--exclude-so`` to override.

The script handles two-row Excel headers (``--header-rows 2``, the default
for VarSeq trio CHIP exports). It auto-detects the Sequence Ontology and
Zygosity columns case-insensitively across both header levels.

CLI
---
Folder of per-sample Excel files (one file per sample):

    python coding_variant_filter.py \
        --dir CHIP_DP10_GQ20_PASS/ --pattern '*.xlsx' \
        --header-rows 2 \
        --workdir /tmp/chip_run

Single combined file with a sample-id column:

    python coding_variant_filter.py \
        --file all_samples.csv --sample-col sample \
        --header-rows 1 --workdir /tmp/chip_run

Single VCF (one sample = whole VCF):

    python coding_variant_filter.py \
        --vcf SAMPLE.vcf --so-info-key ANN \
        --workdir /tmp/chip_run

Output
------
Labelled key=value lines (parseable from any agent):

    N_SAMPLES                  <int>
    SUM_AFTER_FILTER           <int, total kept rows across all samples>
    AVERAGE_PER_SAMPLE         <float, mean per-sample count>
    MEDIAN_PER_SAMPLE          <float>
    MIN_PER_SAMPLE / MAX_PER_SAMPLE
    PER_SAMPLE_COUNTS          JSON dict {sample: count}

Always reports the canonical mean even if the question asks for a range —
the agent can compare against any range threshold.
"""

from __future__ import annotations

import argparse
import glob
import gzip
import json
import os
import statistics
import sys
from pathlib import Path
from typing import Iterable

import pandas as pd


DEFAULT_EXCLUDE_SO = (
    "intron_variant",
    "intergenic_variant",
    "3_prime_UTR_variant",
    "5_prime_UTR_variant",
    "upstream_gene_variant",
    "downstream_gene_variant",
)


def reject_canonical(path: Path) -> None:
    """Refuse to write inside any the input data folder path."""
    for part in path.resolve().parts:
        if part.startswith("CapsuleFolder-"):
            sys.stderr.write(
                f"Refusing to write inside a input data folder directory: {path}\n"
                f"Pass --workdir <path-outside-input>, e.g. --workdir /tmp/chip_run.\n"
            )
            sys.exit(2)


def find_column(df: pd.DataFrame, *needles: str) -> object:
    """Return the first column whose stringified form contains any needle (case-insensitive)."""
    needles_lower = [n.lower() for n in needles]
    for c in df.columns:
        s = str(c).lower()
        if any(n in s for n in needles_lower):
            return c
    return None


def count_one_table(
    df: pd.DataFrame,
    *,
    apply_zygosity_filter: bool,
    exclude_so: Iterable[str],
) -> int:
    """Count rows after filtering reference calls and non-coding SO terms."""
    so_col = find_column(df, "sequence ontology", "consequence", "effect")
    if so_col is None:
        raise ValueError(
            "Could not find a Sequence Ontology / Consequence / Effect column. "
            f"Columns: {list(df.columns)[:20]}"
        )

    keep = pd.Series([True] * len(df))

    if apply_zygosity_filter:
        zyg_col = find_column(df, "zygosity")
        if zyg_col is not None:
            keep &= df[zyg_col].astype(str).str.strip().str.lower() != "reference"

    so_series = df[so_col].astype(str).str.strip()
    excl = {e.lower() for e in exclude_so}
    keep &= ~so_series.str.lower().isin(excl)

    return int(keep.sum())


def parse_vcf_so_counts(
    vcf_path: Path,
    *,
    info_key: str = "ANN",
    apply_pass_filter: bool,
    exclude_so: Iterable[str],
) -> int:
    """Count non-header VCF records after dropping non-coding SO terms.

    Looks at the first SO term in the ``ANN`` (SnpEff) or ``CSQ`` (VEP) INFO
    field. Records with no annotation in --info-key are kept (assume coding).
    """
    excl = {e.lower() for e in exclude_so}
    opener = gzip.open if str(vcf_path).endswith(".gz") else open
    kept = 0
    with opener(vcf_path, "rt") as f:
        for line in f:
            if line.startswith("#"):
                continue
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 8:
                continue
            if apply_pass_filter and cols[6] not in ("PASS", "."):
                continue
            info = cols[7]
            so_term = ""
            for entry in info.split(";"):
                if entry.startswith(info_key + "="):
                    payload = entry[len(info_key) + 1 :]
                    first = payload.split(",")[0]
                    fields = first.split("|")
                    # ANN: Allele|Annotation|...; CSQ also has Consequence early
                    if len(fields) >= 2:
                        so_term = fields[1]
                    break
            if so_term and so_term.lower() in excl:
                continue
            kept += 1
    return kept


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--dir", help="directory of per-sample tables (one file per sample)")
    src.add_argument("--file", help="single combined table with --sample-col")
    src.add_argument("--vcf", help="single VCF file (treated as one sample)")

    p.add_argument("--pattern", default="*.xlsx",
                   help="glob pattern within --dir (default: *.xlsx)")
    p.add_argument("--header-rows", type=int, default=2,
                   help="1 or 2 (default 2 = clinical VarSeq style multi-row header)")
    p.add_argument("--sample-col", help="column name holding sample IDs (only with --file)")
    p.add_argument("--no-zygosity-filter", action="store_true",
                   help="skip the Zygosity != 'Reference' filter (useful when input "
                        "is already non-reference)")
    p.add_argument("--exclude-so", default=",".join(DEFAULT_EXCLUDE_SO),
                   help="comma-separated SO terms to exclude (default: intronic / "
                        "intergenic / 5'UTR / 3'UTR / upstream / downstream)")
    p.add_argument("--so-info-key", default="ANN",
                   help="VCF INFO key holding SO annotation (default ANN; use CSQ for VEP)")
    p.add_argument("--no-pass-filter", action="store_true",
                   help="for --vcf: do NOT require FILTER == PASS")
    p.add_argument("--workdir", help="scratch directory (refuses input data folder paths). "
                                     "Optional - script never needs to write large files.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if args.workdir:
        wd = Path(args.workdir)
        reject_canonical(wd)
        wd.mkdir(parents=True, exist_ok=True)

    exclude_so = [s.strip() for s in args.exclude_so.split(",") if s.strip()]
    counts: dict[str, int] = {}

    if args.dir:
        files = sorted(glob.glob(os.path.join(args.dir, args.pattern)))
        if not files:
            sys.stderr.write(f"No files match {args.dir}/{args.pattern}\n")
            return 1
        for f in files:
            name = os.path.splitext(os.path.basename(f))[0]
            if f.endswith((".xlsx", ".xls")):
                if args.header_rows == 2:
                    df = pd.read_excel(f, header=[0, 1])
                else:
                    df = pd.read_excel(f)
            else:
                df = pd.read_csv(f)
            counts[name] = count_one_table(
                df,
                apply_zygosity_filter=not args.no_zygosity_filter,
                exclude_so=exclude_so,
            )
    elif args.file:
        if not args.sample_col:
            sys.stderr.write("--sample-col is required with --file\n")
            return 1
        path = args.file
        if path.endswith((".xlsx", ".xls")):
            df = pd.read_excel(path, header=[0, 1] if args.header_rows == 2 else 0)
        else:
            df = pd.read_csv(path)
        sample_col = args.sample_col
        # When header_rows == 2, sample_col may be a single string matching either level
        if args.header_rows == 2:
            cands = [c for c in df.columns if sample_col in str(c)]
            if cands:
                sample_col = cands[0]
        for name, sub in df.groupby(sample_col):
            counts[str(name)] = count_one_table(
                sub,
                apply_zygosity_filter=not args.no_zygosity_filter,
                exclude_so=exclude_so,
            )
    else:
        # --vcf
        vcf_path = Path(args.vcf).resolve()
        if not vcf_path.exists():
            sys.stderr.write(f"VCF not found: {vcf_path}\n")
            return 1
        n = parse_vcf_so_counts(
            vcf_path,
            info_key=args.so_info_key,
            apply_pass_filter=not args.no_pass_filter,
            exclude_so=exclude_so,
        )
        counts[vcf_path.stem] = n

    if not counts:
        sys.stderr.write("No samples were counted.\n")
        return 1

    values = list(counts.values())
    total = sum(values)
    mean = statistics.mean(values)
    median = statistics.median(values)

    print(f"N_SAMPLES={len(values)}")
    print(f"SUM_AFTER_FILTER={total}")
    print(f"AVERAGE_PER_SAMPLE={mean:.4f}")
    print(f"MEDIAN_PER_SAMPLE={median}")
    print(f"MIN_PER_SAMPLE={min(values)}")
    print(f"MAX_PER_SAMPLE={max(values)}")
    print(f"EXCLUDED_SO_TERMS={','.join(exclude_so)}")
    print(f"ZYGOSITY_FILTER_APPLIED={not args.no_zygosity_filter}")
    print("---")
    # JSON dump for full per-sample counts
    print("PER_SAMPLE_COUNTS=" + json.dumps(counts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
