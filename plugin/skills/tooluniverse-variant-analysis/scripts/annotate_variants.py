#!/usr/bin/env python3
"""
Standalone Variant Annotation Script

Annotate variants from VCF using ToolUniverse annotation tools.

Usage:
    python annotate_variants.py input.vcf
    python annotate_variants.py input.vcf --output annotated.tsv --max-annotate 100
    python annotate_variants.py input.vcf --rsid-only --sample TUMOR
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path to import python_implementation
sys.path.insert(0, str(Path(__file__).parent.parent))

from python_implementation import parse_vcf, batch_annotate_variants

try:
    from tooluniverse import ToolUniverse
except ImportError:
    print("Error: ToolUniverse not installed. Install with: pip install tooluniverse")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Annotate variants using ToolUniverse tools"
    )
    parser.add_argument("vcf_path", help="Path to input VCF file")
    parser.add_argument(
        "--output", help="Output TSV file for annotations (default: stdout)"
    )
    parser.add_argument(
        "--max-annotate",
        type=int,
        default=100,
        help="Maximum variants to annotate (default: 100)",
    )
    parser.add_argument(
        "--rsid-only",
        action="store_true",
        help="Only annotate variants with rsIDs (more reliable)",
    )
    parser.add_argument(
        "--sample", help="Sample name for displaying VAF/depth (default: first)"
    )

    args = parser.parse_args()

    # Parse VCF
    print(f"Parsing VCF: {args.vcf_path}...", file=sys.stderr)
    vcf_data = parse_vcf(args.vcf_path)
    print(f"Parsed {len(vcf_data.variants)} variants", file=sys.stderr)

    # Filter to rsID variants if requested
    if args.rsid_only:
        variants = [
            v for v in vcf_data.variants if v.vid and v.vid.startswith("rs")
        ]
        print(f"Found {len(variants)} variants with rsIDs", file=sys.stderr)
    else:
        variants = vcf_data.variants

    # Load ToolUniverse
    print("Loading ToolUniverse...", file=sys.stderr)
    tu = ToolUniverse()
    tu.load_tools()
    print("ToolUniverse loaded", file=sys.stderr)

    # Annotate
    print(
        f"Annotating up to {args.max_annotate} variants (this may take a minute)...",
        file=sys.stderr,
    )
    annotations = batch_annotate_variants(tu, variants, max_annotate=args.max_annotate)
    print(f"Annotated {len(annotations)} variants", file=sys.stderr)

    # Determine sample for VAF/depth display
    sample = args.sample or (vcf_data.samples[0] if vcf_data.samples else None)

    # Write output
    if args.output:
        output_file = open(args.output, "w")
    else:
        output_file = sys.stdout

    try:
        # Write header
        headers = [
            "variant_key",
            "chrom",
            "pos",
            "ref",
            "alt",
            "gene_symbol",
            "mutation_type",
            "protein_change",
            "clinvar_classification",
            "gnomad_af",
            "cadd_phred",
        ]
        if sample:
            headers.extend(["vaf", "depth"])

        output_file.write("\t".join(headers) + "\n")

        # Write annotations
        for ann in annotations:
            # Get VAF/depth if sample specified
            vaf = None
            depth = None
            if sample and ann.variant and ann.variant.samples:
                sample_data = ann.variant.samples.get(sample, {})
                vaf = sample_data.get("AF") or sample_data.get("VAF")
                depth = sample_data.get("DP")

            row = [
                ann.variant_key or "",
                ann.chrom or "",
                str(ann.pos) if ann.pos else "",
                ann.ref or "",
                ann.alt or "",
                ann.gene_symbol or "",
                ann.mutation_type or "",
                ann.protein_change or "",
                ann.clinvar_classification or "",
                f"{ann.gnomad_af:.6f}" if ann.gnomad_af is not None else "",
                f"{ann.cadd_phred:.2f}" if ann.cadd_phred is not None else "",
            ]

            if sample:
                row.append(f"{vaf:.4f}" if vaf is not None else "")
                row.append(str(depth) if depth is not None else "")

            output_file.write("\t".join(row) + "\n")

        print(f"Wrote {len(annotations)} annotated variants", file=sys.stderr)

        # Print summary statistics
        print("\n=== Annotation Summary ===", file=sys.stderr)

        clinvar_count = sum(
            1 for a in annotations if a.clinvar_classification is not None
        )
        print(f"Variants with ClinVar data: {clinvar_count}", file=sys.stderr)

        pathogenic_count = sum(
            1
            for a in annotations
            if a.clinvar_classification
            and "pathogenic" in a.clinvar_classification.lower()
        )
        print(
            f"  Pathogenic/Likely Pathogenic: {pathogenic_count}", file=sys.stderr
        )

        gnomad_count = sum(1 for a in annotations if a.gnomad_af is not None)
        print(f"Variants with gnomAD AF: {gnomad_count}", file=sys.stderr)

        rare_count = sum(
            1 for a in annotations if a.gnomad_af is not None and a.gnomad_af < 0.01
        )
        print(f"  Rare variants (AF < 1%): {rare_count}", file=sys.stderr)

        cadd_count = sum(1 for a in annotations if a.cadd_phred is not None)
        print(f"Variants with CADD score: {cadd_count}", file=sys.stderr)

        high_cadd_count = sum(
            1 for a in annotations if a.cadd_phred is not None and a.cadd_phred >= 20
        )
        print(
            f"  High CADD score (≥20): {high_cadd_count}", file=sys.stderr
        )

    finally:
        if args.output:
            output_file.close()


if __name__ == "__main__":
    main()
