#!/usr/bin/env python3
"""Compute methylation CpG-density statistics from a long-format methylation CSV.

Long-format methylation CSVs typically have one row per (sample × CpG site),
so `len(df)` >> `n_unique_sites`. Several published metrics aggregate across
chromosomes, sites, or samples in subtly different ways. This script makes
those aggregations explicit and deterministic.

Usage:
    python methylation_density.py \\
        --cpg <CpG csv with Pos, Chromosome, MethylationPercentage> \\
        --chr-lengths <CSV with Chromosome, Length> \\
        [--filter-meth-extremes 90 10] \\
        [--chromosome Z] \\
        [--report all]

What it computes (printed in JSON to stdout):

  rows_total                    # all rows (sample-positions)
  rows_after_filter             # after extreme-methylation filter
  rows_removed                  # rows filtered out (= rows_total - rows_after_filter)
  unique_pos_total              # unique CpG positions (deduped by Pos)
  unique_pos_after_filter       # unique positions where any row passed filter
  unique_pos_removed            # unique positions where NO row passed filter
  total_genome_length           # sum of all chromosome lengths in the chr-lengths file
  density_total_over_genome     # unique_pos_after_filter / total_genome_length
  density_avg_per_chr           # mean of (unique_pos_after_filter[c] / chr_length[c]) over chromosomes
  per_chr                       # dict of chromosome → {n_cpgs, length, density}
  density_chromosome            # if --chromosome X given: unique_pos_after_filter[X] / chr_length[X]
  chisquare_uniform             # chi-square test that per-chromosome CpG counts
                                # match a length-proportional ("uniform density")
                                # expectation: {statistic, df, p_value, n_chr}

Question-to-metric mapping (general):
  "How many sites are removed when filtering ..."   → rows_removed (sample-row level)
  "How many unique CpG sites pass filter"           → unique_pos_after_filter
  "Genome-wide AVERAGE chromosomal density"         → density_avg_per_chr  (mean of per-chr)
  "Density on chromosome X"                         → density_chromosome (single-chr)
  "Total density across genome"                     → density_total_over_genome
  "Chi-square stat for uniform distribution"        → chisquare_uniform.statistic

The chi-square uniformity test mirrors the canonical R idiom
`chisq.test(n_cpgs, p = expected/sum(expected))` where expected counts are
length-proportional (chromosomes with no length match are dropped first).

The "average chromosomal density" metric is the per-chromosome mean,
not total/total — these differ when CpGs are unevenly distributed.
"""

import argparse
import json
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cpg", required=True, type=Path,
                    help="Methylation CSV with Pos, Chromosome, MethylationPercentage columns")
    ap.add_argument("--chr-lengths", required=True, type=Path,
                    help="CSV with Chromosome, Length columns")
    ap.add_argument("--filter-meth-extremes", nargs=2, type=float,
                    metavar=("HIGH", "LOW"),
                    help="Keep rows with MethylationPercentage > HIGH or < LOW. "
                         "Typical: 90 10")
    ap.add_argument("--chromosome",
                    help="Compute density on this single chromosome")
    ap.add_argument("--report", default="all",
                    choices=["all", "rows_removed", "density_avg_per_chr",
                             "density_chromosome", "unique_pos_after_filter"],
                    help="Which metric to print on stdout (default: all as JSON)")
    args = ap.parse_args()

    try:
        import pandas as pd
    except ImportError:
        sys.exit("ERROR: pandas required (pip install pandas)")

    df = pd.read_csv(args.cpg)
    chr_lens = pd.read_csv(args.chr_lengths)
    chr_lens["Chromosome"] = chr_lens["Chromosome"].astype(str)
    df["Chromosome"] = df["Chromosome"].astype(str)

    rows_total = len(df)
    unique_pos_total = df["Pos"].nunique() if "Pos" in df.columns else None

    if args.filter_meth_extremes:
        high, low = args.filter_meth_extremes
        kept = df[(df["MethylationPercentage"] > high) | (df["MethylationPercentage"] < low)]
    else:
        kept = df

    rows_after_filter = len(kept)
    rows_removed = rows_total - rows_after_filter
    unique_pos_after_filter = kept["Pos"].nunique() if "Pos" in kept.columns else None
    unique_pos_removed = (unique_pos_total - unique_pos_after_filter
                          if unique_pos_total is not None else None)

    # Per-chromosome unique positions (after filter) AND raw row counts
    by_chr = (kept.groupby("Chromosome")["Pos"].nunique()
              .reset_index().rename(columns={"Pos": "n_cpgs"}))
    by_chr_rows = (kept.groupby("Chromosome").size()
                   .reset_index(name="n_rows"))
    by_chr = by_chr.merge(by_chr_rows, on="Chromosome", how="left")
    by_chr = by_chr.merge(chr_lens, on="Chromosome", how="left").dropna(subset=["Length"])
    by_chr["density"] = by_chr["n_cpgs"] / by_chr["Length"]

    total_genome_length = float(chr_lens["Length"].sum())
    density_total_over_genome = (
        unique_pos_after_filter / total_genome_length
        if unique_pos_after_filter is not None else None
    )
    density_avg_per_chr = float(by_chr["density"].mean()) if len(by_chr) else None

    density_chromosome = None
    density_chromosome_over_genome_rows = None
    density_chromosome_over_genome_unique = None
    if args.chromosome:
        target = str(args.chromosome).upper()
        sub = by_chr[by_chr["Chromosome"].str.upper() == target]
        if not sub.empty:
            density_chromosome = float(sub["density"].iloc[0])
            # Alternative interpretation: per-chromosome filtered count
            # divided by TOTAL genome length (e.g. "density of chrZ CpGs in
            # the Zebra Finch genome" — when 'in the X genome' implies a
            # genome-wide denominator instead of per-chromosome).
            density_chromosome_over_genome_rows = float(
                sub["n_rows"].iloc[0] / total_genome_length
            )
            density_chromosome_over_genome_unique = float(
                sub["n_cpgs"].iloc[0] / total_genome_length
            )

    per_chr = {row["Chromosome"]: {
        "n_cpgs": int(row["n_cpgs"]),
        "n_rows": int(row["n_rows"]),
        "length": int(row["Length"]),
        "density": float(row["density"]),
        "density_over_genome_rows": float(row["n_rows"] / total_genome_length),
        "density_over_genome_unique": float(row["n_cpgs"] / total_genome_length),
    } for _, row in by_chr.iterrows()}

    # Chi-square test: do per-chromosome CpG counts match a length-proportional
    # ("uniform density") expectation? Mirrors the canonical R idiom
    # chisq.test(n_cpgs, p = expected/sum(expected)).
    chisquare_uniform = None
    if len(by_chr) >= 2:
        try:
            from scipy.stats import chisquare as _chisquare

            observed = by_chr["n_cpgs"].astype(float)
            total_cpgs = float(observed.sum())
            total_len = float(by_chr["Length"].sum())
            expected = by_chr["Length"].astype(float) * (total_cpgs / total_len)
            expected = expected / expected.sum() * total_cpgs
            stat, pval = _chisquare(observed.values, expected.values)
            chisquare_uniform = {
                "statistic": float(stat),
                "df": int(len(by_chr) - 1),
                "p_value": float(pval),
                "n_chr": int(len(by_chr)),
            }
        except ImportError:
            chisquare_uniform = {"error": "scipy required for chi-square test"}

    result = {
        "rows_total": rows_total,
        "rows_after_filter": rows_after_filter,
        "rows_removed": rows_removed,
        "unique_pos_total": unique_pos_total,
        "unique_pos_after_filter": unique_pos_after_filter,
        "unique_pos_removed": unique_pos_removed,
        "total_genome_length": total_genome_length,
        "density_total_over_genome": density_total_over_genome,
        "density_avg_per_chr": density_avg_per_chr,
        "density_chromosome": density_chromosome,
        "density_chromosome_over_genome_rows": density_chromosome_over_genome_rows,
        "density_chromosome_over_genome_unique": density_chromosome_over_genome_unique,
        "chisquare_uniform": chisquare_uniform,
        "per_chr": per_chr,
    }

    if args.report == "all":
        print(json.dumps(result, indent=2))
    else:
        v = result.get(args.report)
        print(v)


if __name__ == "__main__":
    main()
