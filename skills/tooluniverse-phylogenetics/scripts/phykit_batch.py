#!/usr/bin/env python3
"""Batch PhyKIT computation for phylogenetics benchmarks.

Runs PhyKIT functions (treeness, saturation, dvmc, long_branch_score,
total_tree_length, parsimony_informative) on all tree/alignment files
in a directory and outputs summary statistics.

Usage:
    python phykit_batch.py --dir scogs_fungi --function treeness --ext .treefile
    python phykit_batch.py --dir alignments --function saturation --tree-dir trees --ext .fa --tree-ext .treefile
    python phykit_batch.py --dir trees --function long_branch_score --ext .treefile --stat mean
    python phykit_batch.py --dir alignments --function gap_percentage --ext .fa
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run_phykit(function: str, filepath: str, tree_path: str = "") -> str | None:
    """Run a single phykit command and return stdout."""
    cmd = ["phykit", function, filepath]
    if tree_path and function == "saturation":
        cmd.extend(["-t", tree_path])
    # long_branch_score / patristic_distances default to labeled summary stats;
    # -v emits one value per taxon/pair so we can compute our own summary.
    if function in ("long_branch_score", "patristic_distances"):
        cmd.append("-v")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if r.returncode == 0:
            return r.stdout.strip()
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def _parse_tsv_last_column(output: str) -> list[float]:
    """Parse per-row numeric values from phykit tab-separated output."""
    lines = [l for l in output.split("\n") if l.strip()]
    try:
        return [float(l.split("\t")[-1]) for l in lines if "\t" in l]
    except (ValueError, IndexError):
        return []


def _median(sorted_values: list[float]) -> float:
    n = len(sorted_values)
    if n % 2:
        return sorted_values[n // 2]
    return (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2


def _summarize_per_tree(values_in: list[float], stat: str) -> float | None:
    """Apply per-tree summary (mean/median/sum). Returns None if unsupported."""
    if not values_in:
        return None
    if stat == "mean":
        return sum(values_in) / len(values_in)
    if stat == "median":
        return _median(sorted(values_in))
    if stat == "sum":
        return sum(values_in)
    return None


def compute_gap_percentage(alignment_dir: str, ext: str) -> dict:
    """Compute total gap percentage across all alignments."""
    total_gaps = 0
    total_positions = 0
    files_processed = 0

    for f in sorted(Path(alignment_dir).glob(f"*{ext}")):
        with open(f) as fh:
            seqs = []
            current = []
            for line in fh:
                line = line.strip()
                if line.startswith(">"):
                    if current:
                        seqs.append("".join(current))
                    current = []
                else:
                    current.append(line)
            if current:
                seqs.append("".join(current))

        for seq in seqs:
            total_positions += len(seq)
            total_gaps += seq.count("-")
        files_processed += 1

    pct = (total_gaps / total_positions * 100) if total_positions > 0 else 0
    return {
        "total_gaps": total_gaps,
        "total_positions": total_positions,
        "gap_percentage": round(pct, 1),
        "files_processed": files_processed,
    }


def main():
    parser = argparse.ArgumentParser(description="Batch PhyKIT computation")
    parser.add_argument("--dir", required=True, help="Directory with tree/alignment files")
    parser.add_argument(
        "--function",
        required=True,
        choices=[
            "treeness", "saturation", "dvmc", "long_branch_score",
            "total_tree_length", "parsimony_informative", "gap_percentage",
            "evolutionary_rate", "patristic_distances",
        ],
    )
    parser.add_argument("--ext", default=".treefile", help="File extension to match")
    parser.add_argument("--tree-dir", default="", help="Tree directory (for saturation)")
    parser.add_argument("--tree-ext", default=".treefile", help="Tree file extension")
    parser.add_argument(
        "--stat",
        default="all",
        choices=["all", "mean", "median", "min", "max"],
        help="Summary statistic to compute",
    )
    parser.add_argument(
        "--per-tree-stat",
        default="",
        choices=["", "mean", "median", "sum"],
        help="For long_branch_score: how to summarize per-tree LB scores (default: use raw output)",
    )
    args = parser.parse_args()

    if args.function == "gap_percentage":
        result = compute_gap_percentage(args.dir, args.ext)
        print(f"Files: {result['files_processed']}")
        print(f"Total positions: {result['total_positions']}")
        print(f"Total gaps: {result['total_gaps']}")
        print(f"Gap percentage: {result['gap_percentage']}%")
        return

    # Find files
    files = sorted(Path(args.dir).glob(f"*{args.ext}"))
    if not files:
        print(f"No files matching *{args.ext} in {args.dir}")
        sys.exit(1)

    print(f"Processing {len(files)} files with phykit {args.function}...", file=sys.stderr)

    values = []
    for f in files:
        tree_path = ""
        if args.tree_dir and args.function == "saturation":
            tree_path = str(Path(args.tree_dir) / f"{f.stem}{args.tree_ext}")
            if not os.path.exists(tree_path):
                continue

        output = run_phykit(args.function, str(f), tree_path)
        if output is None:
            continue

        if args.function == "patristic_distances":
            # Output: one distance per pair of taxa; summarize per tree.
            # Default is mean (standard interpretation of "mean patristic distance").
            pair_values = _parse_tsv_last_column(output)
            if not pair_values:
                continue
            stat = args.per_tree_stat or "mean"
            summary = _summarize_per_tree(pair_values, stat)
            if summary is not None:
                values.append(summary)
        elif args.function == "long_branch_score":
            # LB score outputs one value per taxon; summarize per tree.
            # Default (empty per_tree_stat) flattens all taxa into the global pool.
            taxon_values = _parse_tsv_last_column(output)
            if not taxon_values:
                lines = [l for l in output.split("\n") if l.strip()]
                try:
                    taxon_values = [float(lines[0])]
                except (ValueError, IndexError):
                    continue
            summary = _summarize_per_tree(taxon_values, args.per_tree_stat)
            if summary is not None:
                values.append(summary)
            else:
                values.extend(taxon_values)
        else:
            # Single-value output. `phykit saturation` outputs `slope<TAB>1-slope`;
            # papers typically report 1-slope as "the saturation value", so take
            # the second column when available. Other single-value functions
            # (treeness, dvmc, total_tree_length, evolutionary_rate,
            # parsimony_informative) emit only one column, so first-column
            # extraction is also correct for them.
            first_line = output.split("\n")[0]
            cols = first_line.split("\t")
            try:
                if args.function == "saturation" and len(cols) >= 2:
                    val = float(cols[1])
                else:
                    val = float(cols[0])
                values.append(val)
            except (ValueError, IndexError):
                continue

    if not values:
        print("No values computed")
        sys.exit(1)

    values.sort()
    n = len(values)
    mean = sum(values) / n
    median = _median(values)

    print(f"N: {n}")
    print(f"Mean: {mean:.6f}")
    print(f"Median: {median:.6f}")
    print(f"Min: {min(values):.6f}")
    print(f"Max: {max(values):.6f}")

    if args.stat == "mean":
        print(f"\nAnswer: {mean}")
    elif args.stat == "median":
        print(f"\nAnswer: {median}")
    elif args.stat == "min":
        print(f"\nAnswer: {min(values)}")
    elif args.stat == "max":
        print(f"\nAnswer: {max(values)}")


if __name__ == "__main__":
    main()
