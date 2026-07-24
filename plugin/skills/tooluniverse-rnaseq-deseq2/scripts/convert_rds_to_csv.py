#!/usr/bin/env python3
"""
Convert R RDS files to CSV for Python analysis.

This script bridges R and Python for RNA-seq analysis by:
1. Detecting if R is installed
2. Running R script to convert RDS → CSV
3. Validating the converted data
4. Preparing gene lists for enrichment analysis

Usage:
    python convert_rds_to_csv.py input.rds output.csv
    python convert_rds_to_csv.py input.rds output.csv --filter-upregulated
"""

import subprocess
import os
import sys
import pandas as pd
import argparse

def check_r_installed():
    """Check if R is available"""
    try:
        result = subprocess.run(
            ['R', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False

def convert_rds_to_csv(rds_path, csv_path):
    """Convert RDS file to CSV using R"""

    # Create R conversion script
    r_script = f"""
    # Read RDS (works with or without DESeq2 package)
    result <- readRDS("{rds_path}")

    # Convert to data frame
    result_df <- as.data.frame(result)

    # Write CSV with row names
    write.csv(result_df, "{csv_path}", row.names = TRUE)

    # Print summary
    cat("\\n✓ Converted to CSV\\n")
    cat("  Rows:", nrow(result_df), "\\n")
    cat("  Columns:", ncol(result_df), "\\n")
    cat("  Column names:", paste(colnames(result_df), collapse=", "), "\\n")

    # If looks like DESeq2 results, show stats
    if ("log2FoldChange" %in% colnames(result_df) && "padj" %in% colnames(result_df)) {{
        cat("\\nDESeq2 Results Summary:\\n")
        sig <- sum(result_df$padj < 0.05, na.rm=TRUE)
        up <- sum(result_df$log2FoldChange > 0 & result_df$padj < 0.05, na.rm=TRUE)
        down <- sum(result_df$log2FoldChange < 0 & result_df$padj < 0.05, na.rm=TRUE)
        cat("  Significant (padj < 0.05):", sig, "\\n")
        cat("  Upregulated:", up, "\\n")
        cat("  Downregulated:", down, "\\n")
    }}
    """

    # Write temporary R script
    temp_script = "temp_convert_rds.R"
    with open(temp_script, 'w') as f:
        f.write(r_script)

    try:
        # Run R script
        result = subprocess.run(
            ['Rscript', temp_script],
            capture_output=True,
            text=True,
            timeout=30
        )

        print(result.stdout)

        if result.returncode != 0:
            print(f"ERROR: R conversion failed")
            print(result.stderr)
            return False

        # Clean up temp script
        os.remove(temp_script)
        return True

    except subprocess.TimeoutExpired:
        print("ERROR: R script timed out")
        return False
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return False

def filter_upregulated_genes(csv_path, output_txt=None, padj_thresh=0.05, log2fc_thresh=0):
    """Filter CSV for upregulated genes and save gene list"""

    df = pd.read_csv(csv_path, index_col=0)

    # Check required columns
    if 'log2FoldChange' not in df.columns or 'padj' not in df.columns:
        print(f"WARNING: CSV doesn't have log2FoldChange or padj columns")
        print(f"Available columns: {list(df.columns)}")
        return None

    # Filter upregulated
    upregulated = df[
        (df['log2FoldChange'] > log2fc_thresh) &
        (df['padj'] < padj_thresh)
    ]

    print(f"\n✓ Found {len(upregulated)} upregulated genes")
    print(f"  Criteria: log2FC > {log2fc_thresh}, padj < {padj_thresh}")

    if len(upregulated) == 0:
        return None

    # Show top genes
    print(f"\nTop 10 upregulated genes:")
    top = upregulated.nlargest(10, 'log2FoldChange')
    for idx, row in top.iterrows():
        print(f"  {idx:15s} log2FC={row['log2FoldChange']:6.2f}  padj={row['padj']:.2e}")

    # Save gene list if requested
    if output_txt:
        genes = upregulated.index.tolist()
        with open(output_txt, 'w') as f:
            f.write('\n'.join(genes))
        print(f"\n✓ Saved gene list to: {output_txt}")
        print(f"  Ready for /tooluniverse-gene-enrichment")

    return upregulated

def main():
    parser = argparse.ArgumentParser(
        description="Convert R RDS files to CSV for Python analysis"
    )
    parser.add_argument('rds_file', help='Input RDS file path')
    parser.add_argument('csv_file', help='Output CSV file path')
    parser.add_argument(
        '--filter-upregulated',
        action='store_true',
        help='Filter for upregulated genes (requires DESeq2 format)'
    )
    parser.add_argument(
        '--gene-list',
        help='Output file for gene list (if --filter-upregulated)'
    )
    parser.add_argument(
        '--padj-threshold',
        type=float,
        default=0.05,
        help='Adjusted p-value threshold (default: 0.05)'
    )
    parser.add_argument(
        '--log2fc-threshold',
        type=float,
        default=0,
        help='log2FoldChange threshold (default: 0)'
    )

    args = parser.parse_args()

    # Check inputs
    if not os.path.exists(args.rds_file):
        print(f"ERROR: RDS file not found: {args.rds_file}")
        sys.exit(1)

    # Check R installation
    if not check_r_installed():
        print("ERROR: R is not installed")
        print("\nInstallation options:")
        print("  macOS: brew install r")
        print("  Ubuntu: sudo apt-get install r-base")
        print("  Or visit: https://cran.r-project.org/")
        sys.exit(1)

    print("✓ R is installed")

    # Convert RDS to CSV
    print(f"\nConverting {os.path.basename(args.rds_file)} → {args.csv_file}")
    success = convert_rds_to_csv(args.rds_file, args.csv_file)

    if not success:
        print("\n✗ Conversion failed")
        sys.exit(1)

    print(f"\n✓ Successfully converted to: {args.csv_file}")

    # Filter upregulated genes if requested
    if args.filter_upregulated:
        print(f"\nFiltering upregulated genes...")

        gene_list_file = args.gene_list or args.csv_file.replace('.csv', '_genes.txt')

        upregulated = filter_upregulated_genes(
            args.csv_file,
            output_txt=gene_list_file,
            padj_thresh=args.padj_threshold,
            log2fc_thresh=args.log2fc_threshold
        )

        if upregulated is not None:
            # Save filtered results
            filtered_csv = args.csv_file.replace('.csv', '_upregulated.csv')
            upregulated.to_csv(filtered_csv)
            print(f"✓ Saved filtered results to: {filtered_csv}")

    print("\n" + "="*60)
    print("✅ CONVERSION COMPLETE")
    print("="*60)
    print("\nNext steps:")
    print("  1. Review the CSV file for data quality")
    if args.filter_upregulated:
        print("  2. Use gene list with /tooluniverse-gene-enrichment")
        print("  3. Specify database: KEGG_2021_Human")
    else:
        print("  2. Load CSV with pd.read_csv()")
        print("  3. Continue with DESeq2 analysis workflow")

if __name__ == "__main__":
    main()
