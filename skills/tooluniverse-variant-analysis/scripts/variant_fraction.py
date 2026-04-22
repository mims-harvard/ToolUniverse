#!/usr/bin/env python3
"""Calculate fraction of variants with a specific annotation.

Uses the correct convention: denominator is CODING variants only
(synonymous, missense, stop_gained, frameshift, etc.), excluding
intronic/UTR/intergenic records.

Usage:
    python variant_fraction.py --file variants.xlsx --vaf-threshold 0.3 \
        --annotation synonymous_variant --header-rows 2
"""

import argparse
import sys

import pandas as pd


CODING_SO_TERMS = {
    "synonymous_variant", "missense_variant", "splice_region_variant",
    "stop_gained", "stop_lost", "start_lost", "frameshift_variant",
    "inframe_insertion", "inframe_deletion",
}

NON_CODING_SO_TERMS = {
    "intron_variant", "3_prime_UTR_variant", "5_prime_UTR_variant",
    "upstream_gene_variant", "downstream_gene_variant",
    "intergenic_variant",
}


def main():
    parser = argparse.ArgumentParser(description="Variant fraction calculator")
    parser.add_argument("--file", required=True, help="Variant Excel or CSV file")
    parser.add_argument("--vaf-threshold", type=float, default=0.3,
                       help="VAF threshold (variants below this)")
    parser.add_argument("--annotation", default="synonymous_variant",
                       help="SO annotation to count")
    parser.add_argument("--header-rows", type=int, default=1,
                       help="Number of header rows (1 or 2)")
    parser.add_argument("--vaf-col", default="", help="VAF column name")
    parser.add_argument("--so-col", default="", help="Sequence Ontology column name")
    args = parser.parse_args()

    # Load file
    if args.file.endswith(".xlsx"):
        if args.header_rows == 2:
            df = pd.read_excel(args.file, header=[0, 1])
        else:
            df = pd.read_excel(args.file)
    else:
        df = pd.read_csv(args.file)

    print(f"Loaded: {df.shape}")
    print(f"Columns: {list(df.columns)[:10]}")

    # Find VAF and SO columns
    vaf_col = args.vaf_col
    so_col = args.so_col

    if not vaf_col:
        for col in df.columns:
            col_str = str(col).lower()
            if "variant allele freq" in col_str or "vaf" in col_str:
                vaf_col = col
                break

    if not so_col:
        for col in df.columns:
            col_str = str(col).lower()
            if "sequence ontology" in col_str:
                so_col = col
                break

    if not vaf_col or not so_col:
        print(f"Could not find VAF column ({vaf_col}) or SO column ({so_col})")
        print("Available columns:", list(df.columns))
        sys.exit(1)

    print(f"VAF column: {vaf_col}")
    print(f"SO column: {so_col}")

    # Filter by VAF threshold
    df_filtered = df[pd.to_numeric(df[vaf_col], errors="coerce") < args.vaf_threshold]
    print(f"Variants with VAF < {args.vaf_threshold}: {len(df_filtered)}")

    # Filter to coding variants only
    coding_mask = df_filtered[so_col].astype(str).apply(
        lambda x: any(term in x for term in CODING_SO_TERMS)
    )
    df_coding = df_filtered[coding_mask]
    print(f"Coding variants: {len(df_coding)}")

    # Count target annotation
    target_mask = df_coding[so_col].astype(str).str.contains(args.annotation, na=False)
    n_target = target_mask.sum()
    fraction = n_target / len(df_coding) if len(df_coding) > 0 else 0

    print(f"{args.annotation}: {n_target}")
    print(f"Fraction (coding denominator): {fraction:.4f}")
    print(f"For comparison, naive fraction (all variants): {n_target / len(df_filtered):.4f}")


if __name__ == "__main__":
    main()
