#!/usr/bin/env python3
"""HLA population-coverage for a set of T-cell epitopes (IEDB-style algorithm).

Population coverage = the fraction of individuals in a target population that
carry at least one HLA allele able to present one of your epitopes. ToolUniverse
has no HLA-frequency tool, so this packages the coverage MATH (the reusable part)
plus a small bundled table of common HLA-A/HLA-B allele frequencies for a
first-pass "average / broad" estimate.

For population-SPECIFIC coverage, supply real allele frequencies with
--freq-file (one `ALLELE<TAB>FREQUENCY` per line) from the Allele Frequency Net
Database (allelefrequencies.net) or the IEDB population-coverage tool
(tools.iedb.org/population). Do not over-interpret the bundled default for a
specific ethnicity — it is an approximate average.

Coverage per locus (Hardy-Weinberg): an individual is covered at a locus if they
carry >=1 covered allele; with summed covered-allele frequency p, the covered
fraction = 1 - (1 - p)^2. Loci are combined assuming independence:
overall = 1 - prod_over_loci(1 - coverage_locus).

Usage:
    python population_coverage.py --alleles "HLA-A*02:01,HLA-A*01:01,HLA-B*07:02"
    python population_coverage.py --alleles-file covered.txt --freq-file afnd_eur.tsv
"""

from __future__ import annotations

import argparse
import re
import sys

# Approximate broad-average frequencies for common class-I alleles (illustrative
# first-pass default; use --freq-file with AFND data for a specific population).
DEFAULT_FREQ = {
    "A*01:01": 0.083, "A*02:01": 0.146, "A*03:01": 0.077, "A*11:01": 0.058,
    "A*24:02": 0.085, "A*26:01": 0.030, "A*29:02": 0.018, "A*31:01": 0.025,
    "A*32:01": 0.022, "A*68:01": 0.030,
    "B*07:02": 0.063, "B*08:01": 0.054, "B*15:01": 0.036, "B*18:01": 0.022,
    "B*27:05": 0.018, "B*35:01": 0.044, "B*40:01": 0.038, "B*44:02": 0.040,
    "B*44:03": 0.030, "B*51:01": 0.040,
}


def _locus(allele):
    m = re.match(r"(?:HLA-)?([A-Z]+\d?)\*", allele)
    return m.group(1) if m else allele.split("*")[0].replace("HLA-", "")


def _norm(allele):
    return allele.strip().replace("HLA-", "")


def coverage(covered_alleles, freqs):
    by_locus = {}
    for a in covered_alleles:
        a = _norm(a)
        f = freqs.get(a)
        if f is None:
            continue
        by_locus.setdefault(_locus(a), 0.0)
        by_locus[_locus(a)] += f

    locus_cov = {loc: 1.0 - (1.0 - min(p, 1.0)) ** 2 for loc, p in by_locus.items()}
    not_covered = 1.0
    for c in locus_cov.values():
        not_covered *= 1.0 - c
    overall = 1.0 - not_covered
    return {
        "overall_coverage": round(overall * 100, 1),
        "per_locus_coverage_pct": {loc: round(c * 100, 1) for loc, c in locus_cov.items()},
        "covered_allele_freq_sum_per_locus": {loc: round(p, 4) for loc, p in by_locus.items()},
        "alleles_used": [a for a in (_norm(x) for x in covered_alleles) if a in freqs],
        "alleles_unknown_freq": [a for a in (_norm(x) for x in covered_alleles) if a not in freqs],
    }


def _read_list(path):
    out = []
    for line in open(path):
        out += [x for x in re.split(r"[,\s]+", line.strip()) if x]
    return out


def _read_freqs(path):
    f = {}
    for line in open(path):
        parts = re.split(r"[\t,]", line.strip())
        if len(parts) >= 2:
            try:
                f[_norm(parts[0])] = float(parts[1])
            except ValueError:
                continue
    return f


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--alleles", help="Comma-separated covered HLA alleles")
    p.add_argument("--alleles-file")
    p.add_argument("--freq-file", help="ALLELE<TAB>FREQ table (AFND/IEDB) for a specific population")
    args = p.parse_args(argv)
    alleles = _read_list(args.alleles_file) if args.alleles_file else (args.alleles or "").split(",")
    alleles = [a for a in alleles if a.strip()]
    if not alleles:
        p.error("provide --alleles or --alleles-file (the HLA alleles your epitopes cover)")
    freqs = _read_freqs(args.freq_file) if args.freq_file else DEFAULT_FREQ
    import json

    result = coverage(alleles, freqs)
    result["frequency_source"] = args.freq_file or "bundled broad-average default (approximate)"
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
