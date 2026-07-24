#!/usr/bin/env python3
"""
Standalone Variant Filtering Script

Apply filters to VCF file and output passing/failing variants.

Usage:
    python filter_variants.py input.vcf --min-vaf 0.1 --min-depth 20 --pass-only
    python filter_variants.py input.vcf --output filtered.vcf --min-vaf 0.05 --max-vaf 0.95
    python filter_variants.py input.vcf --mutation-types missense nonsense frameshift
    python filter_variants.py input.vcf --exclude-intronic-intergenic --sample TUMOR
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path to import python_implementation
sys.path.insert(0, str(Path(__file__).parent.parent))

from python_implementation import (
    parse_vcf,
    filter_variants,
    filter_intronic_intergenic,
    filter_non_reference_variants,
    compute_variant_statistics,
    FilterCriteria,
)


def write_vcf_header(vcf_data, output_file):
    """Write VCF header to output file"""
    output_file.write("##fileformat=VCFv4.2\n")
    output_file.write(f"##source=tooluniverse-variant-analysis-filter\n")

    # Write INFO fields
    output_file.write(
        '##INFO=<ID=ANN,Number=.,Type=String,Description="Functional annotations">\n'
    )
    output_file.write(
        '##INFO=<ID=CSQ,Number=.,Type=String,Description="Consequence annotations from VEP">\n'
    )

    # Write FORMAT fields
    output_file.write(
        '##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">\n'
    )
    output_file.write('##FORMAT=<ID=AD,Number=R,Type=Integer,Description="Allelic depths for the ref and alt alleles">\n')
    output_file.write(
        '##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Read depth">\n'
    )
    output_file.write(
        '##FORMAT=<ID=AF,Number=A,Type=Float,Description="Allele frequency">\n'
    )

    # Write header line
    samples = "\t".join(vcf_data.samples) if vcf_data.samples else ""
    output_file.write(
        f"#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\t{samples}\n"
    )


def write_variant(variant, output_file):
    """Write variant to VCF file"""
    # Basic fields
    fields = [
        variant.chrom,
        str(variant.pos),
        variant.vid or ".",
        variant.ref,
        variant.alt,
        str(variant.qual) if variant.qual is not None else ".",
        variant.filter_status or ".",
    ]

    # INFO field
    info_parts = []
    if variant.info:
        for key, value in variant.info.items():
            if value is True:
                info_parts.append(key)
            elif value is not False and value is not None:
                info_parts.append(f"{key}={value}")
    fields.append(";".join(info_parts) if info_parts else ".")

    # FORMAT and sample fields
    if variant.sample_data:
        format_keys = []
        sample_values = []

        for sample, sample_data_dict in variant.sample_data.items():
            if not format_keys:
                # First sample defines FORMAT keys
                format_keys = list(sample_data_dict.keys())

            # Collect values for this sample
            values = []
            for key in format_keys:
                value = sample_data_dict.get(key)
                if value is None:
                    values.append(".")
                else:
                    values.append(str(value))
            sample_values.append(":".join(values))

        fields.append(":".join(format_keys))
        fields.extend(sample_values)
    else:
        fields.append(".")

    output_file.write("\t".join(fields) + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Filter variants from VCF file based on various criteria"
    )
    parser.add_argument("vcf_path", help="Path to input VCF file")
    parser.add_argument(
        "--output", help="Output VCF file for passing variants (default: stdout)"
    )
    parser.add_argument(
        "--output-failing", help="Output VCF file for failing variants"
    )

    # Quality filters
    parser.add_argument(
        "--min-vaf", type=float, help="Minimum variant allele frequency"
    )
    parser.add_argument(
        "--max-vaf", type=float, help="Maximum variant allele frequency"
    )
    parser.add_argument("--min-depth", type=int, help="Minimum read depth")
    parser.add_argument("--min-qual", type=float, help="Minimum QUAL score")
    parser.add_argument("--pass-only", action="store_true", help="Only PASS variants")

    # Type filters
    parser.add_argument(
        "--variant-types",
        nargs="+",
        help="Include only these variant types (SNV INS DEL MNV COMPLEX)",
    )
    parser.add_argument(
        "--mutation-types",
        nargs="+",
        help="Include only these mutation types (missense nonsense synonymous etc.)",
    )
    parser.add_argument(
        "--exclude-consequences",
        nargs="+",
        help="Exclude these consequences (intronic intergenic upstream downstream)",
    )

    # Region filters
    parser.add_argument(
        "--chromosomes", nargs="+", help="Include only these chromosomes"
    )

    # Sample filter
    parser.add_argument(
        "--sample", help="Apply VAF/depth filters to this sample (default: first)"
    )

    # Special filters
    parser.add_argument(
        "--exclude-intronic-intergenic",
        action="store_true",
        help="Remove intronic and intergenic variants",
    )
    parser.add_argument(
        "--non-reference-only",
        action="store_true",
        help="Remove variants where all samples are 0/0",
    )

    # Stats
    parser.add_argument(
        "--stats", action="store_true", help="Print statistics for passing variants"
    )

    args = parser.parse_args()

    # Parse VCF
    print(f"Parsing VCF: {args.vcf_path}...", file=sys.stderr)
    vcf_data = parse_vcf(args.vcf_path)
    print(f"Parsed {len(vcf_data.variants)} variants", file=sys.stderr)

    # Apply filters
    variants = vcf_data.variants

    # Special filters first
    if args.non_reference_only:
        print("Filtering non-reference variants...", file=sys.stderr)
        variants, ref_only = filter_non_reference_variants(variants)
        print(f"  Kept {len(variants)} non-reference variants", file=sys.stderr)

    if args.exclude_intronic_intergenic:
        print("Filtering intronic/intergenic variants...", file=sys.stderr)
        variants, non_coding = filter_intronic_intergenic(variants)
        print(f"  Kept {len(variants)} coding variants", file=sys.stderr)

    # Build filter criteria
    criteria = FilterCriteria(
        min_vaf=args.min_vaf,
        max_vaf=args.max_vaf,
        min_depth=args.min_depth,
        min_qual=args.min_qual,
        pass_only=args.pass_only,
        variant_types=args.variant_types,
        mutation_types=args.mutation_types,
        exclude_consequences=args.exclude_consequences,
        chromosomes=args.chromosomes,
        sample=args.sample,
    )

    # Apply criteria filters
    if any(
        [
            args.min_vaf,
            args.max_vaf,
            args.min_depth,
            args.min_qual,
            args.pass_only,
            args.variant_types,
            args.mutation_types,
            args.exclude_consequences,
            args.chromosomes,
        ]
    ):
        print("Applying filter criteria...", file=sys.stderr)
        passing, failing = filter_variants(variants, criteria)
        print(f"  Passing: {len(passing)} variants", file=sys.stderr)
        print(f"  Failing: {len(failing)} variants", file=sys.stderr)
    else:
        passing = variants
        failing = []

    # Write output
    if args.output:
        output_file = open(args.output, "w")
    else:
        output_file = sys.stdout

    try:
        write_vcf_header(vcf_data, output_file)
        for variant in passing:
            write_variant(variant, output_file)
        print(f"Wrote {len(passing)} passing variants", file=sys.stderr)
    finally:
        if args.output:
            output_file.close()

    # Write failing variants if requested
    if args.output_failing:
        with open(args.output_failing, "w") as f:
            write_vcf_header(vcf_data, f)
            for variant in failing:
                write_variant(variant, f)
        print(f"Wrote {len(failing)} failing variants to {args.output_failing}", file=sys.stderr)

    # Print statistics if requested
    if args.stats:
        stats = compute_variant_statistics(passing)
        print("\n=== Passing Variant Statistics ===", file=sys.stderr)
        print(f"Total: {len(passing)}", file=sys.stderr)
        print(f"Ti/Tv: {stats['ti_tv_ratio']:.3f}", file=sys.stderr)
        print("\nMutation Types:", file=sys.stderr)
        for mtype, count in sorted(
            stats["mutation_types"].items(), key=lambda x: x[1], reverse=True
        ):
            print(f"  {mtype}: {count}", file=sys.stderr)


if __name__ == "__main__":
    main()
