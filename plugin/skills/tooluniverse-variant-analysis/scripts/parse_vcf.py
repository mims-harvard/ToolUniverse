#!/usr/bin/env python3
"""
Standalone VCF Parsing Script

Parse VCF file and output summary statistics or convert to CSV/JSON.

Usage:
    python parse_vcf.py input.vcf
    python parse_vcf.py input.vcf --format csv --output variants.csv
    python parse_vcf.py input.vcf --format json --output variants.json
    python parse_vcf.py input.vcf --stats --sample TUMOR
"""

import sys
import argparse
import json
import csv
from pathlib import Path

# Add parent directory to path to import python_implementation
sys.path.insert(0, str(Path(__file__).parent.parent))

from python_implementation import (
    parse_vcf,
    parse_vcf_cyvcf2,
    compute_variant_statistics,
    variants_to_dataframe,
)


def main():
    parser = argparse.ArgumentParser(
        description="Parse VCF file and output summary or convert to CSV/JSON"
    )
    parser.add_argument("vcf_path", help="Path to VCF file")
    parser.add_argument(
        "--format",
        choices=["stats", "csv", "json"],
        default="stats",
        help="Output format (default: stats)",
    )
    parser.add_argument("--output", help="Output file path (default: stdout)")
    parser.add_argument(
        "--sample", help="Sample name for multi-sample VCFs (default: first sample)"
    )
    parser.add_argument(
        "--max-variants", type=int, default=0, help="Maximum variants to parse (0=all)"
    )
    parser.add_argument(
        "--use-cyvcf2", action="store_true", help="Force use of cyvcf2 parser"
    )

    args = parser.parse_args()

    # Parse VCF
    print(f"Parsing VCF: {args.vcf_path}...", file=sys.stderr)
    if args.use_cyvcf2:
        try:
            vcf_data = parse_vcf_cyvcf2(args.vcf_path, max_variants=args.max_variants)
            print("Using cyvcf2 parser", file=sys.stderr)
        except ImportError:
            print(
                "cyvcf2 not available, falling back to pure Python", file=sys.stderr
            )
            vcf_data = parse_vcf(args.vcf_path, max_variants=args.max_variants)
    else:
        vcf_data = parse_vcf(args.vcf_path, max_variants=args.max_variants)

    print(
        f"Parsed {len(vcf_data.variants)} variants from {len(vcf_data.samples)} samples",
        file=sys.stderr,
    )

    # Determine output
    if args.output:
        output_file = open(args.output, "w")
    else:
        output_file = sys.stdout

    try:
        if args.format == "stats":
            # Compute and print statistics
            stats = compute_variant_statistics(vcf_data.variants)

            output_file.write("=== VCF Summary Statistics ===\n\n")
            output_file.write(f"Input File: {args.vcf_path}\n")
            output_file.write(f"Samples: {', '.join(vcf_data.samples)}\n")
            output_file.write(f"Total Variants: {len(vcf_data.variants)}\n\n")

            output_file.write("--- Variant Types ---\n")
            for vtype, count in stats["variant_types"].items():
                output_file.write(f"{vtype}: {count}\n")

            output_file.write("\n--- Mutation Types ---\n")
            for mtype, count in stats["mutation_types"].items():
                output_file.write(f"{mtype}: {count}\n")

            output_file.write("\n--- Impact Distribution ---\n")
            for impact, count in stats["impacts"].items():
                output_file.write(f"{impact}: {count}\n")

            output_file.write(f"\n--- Quality Metrics ---\n")
            output_file.write(f"Ti/Tv Ratio: {stats['ti_tv_ratio']:.3f}\n")

            if stats.get("sample_stats"):
                output_file.write("\n--- Per-Sample Statistics ---\n")
                for sample, sample_stats in stats["sample_stats"].items():
                    output_file.write(f"\n{sample}:\n")
                    vaf_stats = sample_stats.get('vaf', {})
                    depth_stats = sample_stats.get('depth', {})

                    if vaf_stats:
                        output_file.write(f"  VAF: mean={vaf_stats.get('mean', 0):.3f}, ")
                        output_file.write(f"median={vaf_stats.get('median', 0):.3f}, ")
                        output_file.write(
                            f"range=[{vaf_stats.get('min', 0):.3f}, {vaf_stats.get('max', 0):.3f}]\n"
                        )

                    if depth_stats:
                        output_file.write(
                            f"  Depth: mean={depth_stats.get('mean', 0):.1f}, "
                        )
                        output_file.write(
                            f"median={depth_stats.get('median', 0):.1f}, "
                        )
                        output_file.write(
                            f"range=[{depth_stats.get('min', 0)}, {depth_stats.get('max', 0)}]\n"
                        )

        elif args.format == "csv":
            # Convert to DataFrame and write CSV
            sample = args.sample or vcf_data.samples[0] if vcf_data.samples else None
            df = variants_to_dataframe(vcf_data.variants, sample=sample)

            df.to_csv(output_file, index=False)
            print(f"Wrote {len(df)} variants to CSV", file=sys.stderr)

        elif args.format == "json":
            # Convert to JSON
            sample = args.sample or vcf_data.samples[0] if vcf_data.samples else None
            df = variants_to_dataframe(vcf_data.variants, sample=sample)

            # Convert DataFrame to list of dicts
            records = df.to_dict(orient="records")
            json.dump(records, output_file, indent=2)
            print(f"Wrote {len(records)} variants to JSON", file=sys.stderr)

    finally:
        if args.output:
            output_file.close()

    print("Done!", file=sys.stderr)


if __name__ == "__main__":
    main()
