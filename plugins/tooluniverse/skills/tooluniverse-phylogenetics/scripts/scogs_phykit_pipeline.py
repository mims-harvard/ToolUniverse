#!/usr/bin/env python3
"""Run PhyKIT metrics on pre-computed BUSCO single-copy ortholog (SCOGs) trees.

Usage:
    python scogs_phykit_pipeline.py --data-folder /path/to/data \\
        --metric treeness --group fungi
    python scogs_phykit_pipeline.py --data-folder /path/to/data \\
        --metric long_branch_score --group fungi --extra "-v"

Why this exists (RULE ZERO for BUSCO-orthology phylogenetics questions):
    Some phylogenetics datasets ship with `scogs_fungi.zip` and
    `scogs_animals.zip`, which contain the pre-computed alignments
    (`*.faa.mafft.clipkit`) AND trees (`*.faa.mafft.clipkit.treefile`)
    from the original analysis. The reference answers come from running
    PhyKIT on THESE files. Re-running BUSCO → MAFFT → IQ-TREE from scratch
    produces slightly different numbers (different IQ-TREE seed, ClipKit
    decisions, MAFFT version) AND takes hours.

    This script:
      1. Auto-extracts scogs_<group>.zip into a workspace tmpdir if not
         already extracted.
      2. Iterates each ortholog's pre-built alignment+tree.
      3. Runs `phykit <metric>` per ortholog.
      4. Emits a TSV: gene_id <TAB> value [<TAB> value2 ...].

    The agent then reads the TSV and computes whatever aggregate the
    question asks for (median, mean, max, percentage above threshold,
    Mann-Whitney between groups, etc.) — but the per-gene metrics are
    canonical because they came from the original alignments+trees.

Supported metrics (PhyKIT functions):
    treeness, dvmc, long_branch_score, total_tree_length,
    parsimony_informative, saturation, treeness_over_rcv (TreeOverRCV),
    rcv (RCV), evolutionary_rate (Evolutionary Rate),
    patristic_distances (mean / median across pairs)

For metrics that require BOTH alignment and tree (e.g.,
treeness_over_rcv, saturation), the script auto-finds the matching
alignment file alongside the tree.
"""

import argparse
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path


# Metrics that take just a tree
METRIC_TREE_ONLY = {
    "treeness", "dvmc", "long_branch_score", "total_tree_length",
    "evolutionary_rate", "patristic_distances",
}

# Metrics that take an alignment
METRIC_ALN_ONLY = {
    "rcv", "parsimony_informative",
}

# Metrics that take both alignment AND tree
METRIC_ALN_AND_TREE = {
    "treeness_over_rcv", "saturation",
}

ALL_METRICS = METRIC_TREE_ONLY | METRIC_ALN_ONLY | METRIC_ALN_AND_TREE


def ensure_extracted(capsule: Path, group: str) -> Path:
    """Return the directory containing extracted scogs_<group>/ files.

    If already extracted (under a tmp workspace), return that path. Else
    extract scogs_<group>.zip into a writable workspace.
    """
    zip_name = f"scogs_{group}.zip"
    zip_path = capsule / zip_name
    if not zip_path.exists():
        sys.exit(f"ERROR: {zip_name} not found in {capsule}")

    # Extract under <data-folder>/scogs_<group>_extracted/ (the data
    # folder is the writable per-question workspace passed by the caller).
    out_dir = capsule / f"scogs_{group}_extracted"
    if out_dir.exists() and any(out_dir.iterdir()):
        return out_dir
    out_dir.mkdir(exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(out_dir)
    return out_dir


def find_orthologs(extracted: Path) -> list[tuple[str, Path | None, Path | None]]:
    """Return (gene_id, alignment_path, tree_path) tuples for each ortholog.

    Alignment preference order (best -> fallback):
      .faa.mafft.clipkit   (trimmed, canonical for tree-paired metrics)
      .faa.mafft           (untrimmed MAFFT — used when data folder lacks clipkit)
      .faa                 (raw, last-resort)
    Tree preference:
      .faa.mafft.clipkit.treefile
      .treefile

    Some data folders ship only `.faa` + `.faa.mafft` (no clipkit, no trees);
    others ship the full chain with trees. The fallback is critical for
    alignment-only metrics (parsimony_informative, rcv) where the answer
    must come from the canonical alignment, NOT a fresh MAFFT/CLIPKIT
    re-run that would diverge from the reference.
    """
    genes: dict[str, dict[str, Path | None]] = {}
    for p in extracted.rglob("*"):
        if p.is_dir():
            continue
        name = p.name
        if not name[:1].isdigit():
            continue
        stem = name.split(".")[0]
        if stem not in genes:
            genes[stem] = {"raw": None, "mafft": None, "clipkit": None, "tree": None}
        if name.endswith(".faa.mafft.clipkit.treefile"):
            genes[stem]["tree"] = p
        elif name.endswith(".treefile") and genes[stem].get("tree") is None:
            genes[stem]["tree"] = p
        elif name.endswith(".faa.mafft.clipkit"):
            genes[stem]["clipkit"] = p
        elif name.endswith(".faa.mafft"):
            genes[stem]["mafft"] = p
        elif name.endswith(".faa"):
            genes[stem]["raw"] = p

    out = []
    for g, slots in sorted(genes.items()):
        aln = slots["clipkit"] or slots["mafft"] or slots["raw"]
        out.append((g, aln, slots["tree"]))
    return out


# Some metrics in this script's vocabulary do NOT map 1-to-1 to phykit
# CLI subcommands. `parsimony_informative` is the canonical name in the
# scientific literature and skill text, but phykit's CLI exposes it as
# `parsimony_informative_sites` (alias `pis`). The literal `parsimony_informative`
# command returns the help banner with exit code != 0 — silently giving zero
# computed values. Translate at the boundary.
PHYKIT_CLI_ALIAS = {
    "parsimony_informative": "parsimony_informative_sites",
}


def run_phykit(metric: str, aln: Path | None, tree: Path | None,
               extra: list[str]) -> str | None:
    cli = PHYKIT_CLI_ALIAS.get(metric, metric)
    cmd = ["phykit", cli]
    if metric in METRIC_TREE_ONLY:
        if not tree:
            return None
        cmd.append(str(tree))
    elif metric in METRIC_ALN_ONLY:
        if not aln:
            return None
        cmd.append(str(aln))
    elif metric in METRIC_ALN_AND_TREE:
        if not (aln and tree):
            return None
        cmd.extend([str(aln), str(tree)])
    else:
        return None
    if extra:
        cmd.extend(extra)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if r.returncode == 0:
            return r.stdout.strip()
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def alignment_gap_percentage(aln_path: Path) -> float | None:
    """Return % of gap characters in this alignment (FASTA), or None on failure.

    Uses Biopython if available, else parses FASTA manually. Counts gap
    characters '-' over total alignment characters (including gaps).
    """
    try:
        from Bio import AlignIO
        aln = AlignIO.read(str(aln_path), "fasta")
        total = sum(len(rec.seq) for rec in aln)
        gaps = sum(str(rec.seq).count("-") for rec in aln)
        return (100.0 * gaps / total) if total else None
    except Exception:
        try:
            total = 0
            gaps = 0
            with open(aln_path) as f:
                for line in f:
                    if line.startswith(">"):
                        continue
                    s = line.strip()
                    total += len(s)
                    gaps += s.count("-")
            return (100.0 * gaps / total) if total else None
        except Exception:
            return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-folder", "--capsule", required=True, type=Path,
                    dest="data_folder",
                    help="Path to the data folder containing scogs_*.zip")
    ap.add_argument("--group", required=True, choices=["fungi", "animals"])
    ap.add_argument("--metric", required=True, choices=sorted(ALL_METRICS))
    ap.add_argument("--extra", default="",
                    help="Extra args to pass to phykit (e.g. '-v').")
    ap.add_argument("--out", help="Output TSV path. Default: stdout.")
    ap.add_argument(
        "--min-gap-pct", type=float, default=None,
        help="Only include orthologs whose alignment has gap%% >= this value. "
             "Use to compute metrics on the high-gap subset (e.g., "
             "'max treeness/RCV in genes with >70%% alignment gaps' → "
             "--min-gap-pct 70).",
    )
    ap.add_argument(
        "--max-gap-pct", type=float, default=None,
        help="Only include orthologs whose alignment has gap%% <= this value.",
    )
    args = ap.parse_args()

    extra_args = args.extra.split() if args.extra else []
    extracted = ensure_extracted(args.data_folder, args.group)
    orthologs = find_orthologs(extracted)

    # Optional gap-percentage filter: keep only orthologs whose alignment
    # gap% falls in [min, max]. Critical for "max X in genes with >Y% gaps"
    # questions — apply filter BEFORE the aggregation.
    if args.min_gap_pct is not None or args.max_gap_pct is not None:
        before = len(orthologs)
        kept = []
        for gene, aln, tree in orthologs:
            if aln is None:
                continue
            gp = alignment_gap_percentage(aln)
            if gp is None:
                continue
            if args.min_gap_pct is not None and gp < args.min_gap_pct:
                continue
            if args.max_gap_pct is not None and gp > args.max_gap_pct:
                continue
            kept.append((gene, aln, tree))
        print(f"# gap filter: kept {len(kept)}/{before} orthologs "
              f"(min={args.min_gap_pct} max={args.max_gap_pct})",
              file=sys.stderr)
        orthologs = kept

    print(f"# {len(orthologs)} {args.group} orthologs", file=sys.stderr)
    print(f"# metric: {args.metric}", file=sys.stderr)
    t0 = time.time()

    rows = []
    for gene, aln, tree in orthologs:
        out = run_phykit(args.metric, aln, tree, extra_args)
        rows.append((gene, out or ""))

    elapsed = time.time() - t0
    print(f"# elapsed: {elapsed:.1f}s "
          f"({sum(1 for _, v in rows if v)}/{len(rows)} computed)",
          file=sys.stderr)

    sink = open(args.out, "w") if args.out else sys.stdout
    sink.write(f"gene_id\t{args.metric}\n")
    for gene, val in rows:
        sink.write(f"{gene}\t{val}\n")
    if args.out:
        sink.close()


if __name__ == "__main__":
    main()
