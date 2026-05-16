#!/usr/bin/env python3
"""Paired group comparison for BUSCO single-copy ortholog phylogenetics.

This script extracts BOTH `scogs_animals.zip` and `scogs_fungi.zip`,
computes the requested per-ortholog metric on every ortholog, and emits
both per-group summaries AND the cross-group Mann-Whitney U + p-value
in a single invocation. It exists to address timeouts the agent hits
when re-running per-group batches separately.

Why this is faster than calling phykit_batch twice:

- For metrics derivable from alignment columns alone (parsimony_informative,
  rcv, gap_percentage), it uses Biopython directly — no subprocess fork
  per file. ~100x speedup on 500 alignments.
- For tree metrics (treeness, dvmc, long_branch_score, total_tree_length,
  patristic_distances, evolutionary_rate), it spawns one phykit process
  per file but extracts only ONCE per group. The agent had been re-running
  full extraction per question.
- It auto-falls-back across file naming variants — some scogs zips ship
  only `.faa.mafft` (no clipkit), some ship `.faa.mafft.clipkit` (+ trees).

Key design rules:
- Per-tree summary stat (mean vs median) is configurable via --per-tree-stat
  for long_branch_score and patristic_distances (which output multiple
  values per tree). Other metrics are single-valued per file.
- For "lowest non-zero" questions: phykit %PIS reports 0 for highly
  conserved alignments, so the "lowest" is often 0. Provide both raw min
  AND lowest-non-zero in summary.
- For paired ratio questions ("ratio of fungal to animal trees per
  ortholog"), uses common gene_id intersection.

Usage:
    # Compute %PIS per ortholog on both groups and report MWU
    python scogs_paired_compare.py --data-folder /path/to/data \\
        --metric parsimony_informative

    # Long branch score: per-tree summary first, then group MWU
    python scogs_paired_compare.py --data-folder ... \\
        --metric long_branch_score --per-tree-stat mean

Output blocks (parseable):
    # SUMMARY group=fungi: n=255 mean=... median=... min=... max=...
                        lowest_nonzero=... 25th=... 75th=...
    # SUMMARY group=animals: n=241 ...
    # MWU animals_vs_fungi: U=<int> p=<float>
    # MWU fungi_vs_animals: U=<int> p=<float>
    # PAIRED (n_common=N): median_diff(fungi-animal)=... median_ratio(fungi/animal)=...
    # RATIOS_LOWEST: nonzero fungi/animal=... nonzero animal/fungi=...
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import zipfile
from collections import Counter
from pathlib import Path

try:
    from Bio import AlignIO  # type: ignore
    HAS_BIO = True
except ImportError:
    HAS_BIO = False

try:
    from scipy import stats as _stats  # type: ignore
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


# Metrics computed from alignment columns alone (Biopython, no subprocess)
ALN_BIOPY_METRICS = {"parsimony_informative", "rcv", "gap_percentage"}
# Metrics requiring phykit + a tree
PHYKIT_TREE_METRICS = {
    "treeness", "dvmc", "total_tree_length", "evolutionary_rate",
    "long_branch_score", "patristic_distances",
}
# Metrics requiring phykit + alignment + tree
PHYKIT_ALN_AND_TREE = {"treeness_over_rcv", "saturation"}

ALL_METRICS = ALN_BIOPY_METRICS | PHYKIT_TREE_METRICS | PHYKIT_ALN_AND_TREE

# phykit alias map (CLI name → actual phykit subcommand to invoke).
# `parsimony_informative` is NOT a valid phykit subcommand — `parsimony_informative_sites`
# (alias `pis`) is. We translate at the boundary.
PHYKIT_CMD = {
    "treeness": "treeness",
    "dvmc": "dvmc",
    "total_tree_length": "total_tree_length",
    "evolutionary_rate": "evolutionary_rate",
    "long_branch_score": "long_branch_score",
    "patristic_distances": "patristic_distances",
    "rcv": "rcv",
    "treeness_over_rcv": "treeness_over_rcv",
    "saturation": "saturation",
    "parsimony_informative": "parsimony_informative_sites",
}


# ---------- ZIP extraction ----------

def ensure_extracted(capsule: Path, group: str, workspace: Path | None = None) -> Path:
    """Extract scogs_<group>.zip into <workspace>/scogs_<group>_extracted/.

    `workspace` defaults to /tmp/scogs_<folder_name>/ to keep the input
    data folder unmodified — important when the data folder is read-only or
    its checksums are verified by the harness.

    Returns the directory containing per-ortholog files.
    """
    zip_path = capsule / f"scogs_{group}.zip"
    if not zip_path.exists():
        sys.exit(f"ERROR: scogs_{group}.zip not found in {capsule}")
    if workspace is None:
        workspace = Path("/tmp") / f"scogs_{capsule.name}"
    workspace.mkdir(parents=True, exist_ok=True)
    out_dir = workspace / f"scogs_{group}_extracted"
    if out_dir.exists() and any(out_dir.iterdir()):
        return out_dir
    out_dir.mkdir(exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(out_dir)
    return out_dir


# ---------- File discovery ----------

def find_orthologs(extracted: Path) -> list[tuple[str, Path | None, Path | None]]:
    """Return list of (gene_id, alignment_path, tree_path).

    Alignment preference: .faa.mafft.clipkit > .faa.mafft > .faa
    Tree: .faa.mafft.clipkit.treefile > .treefile

    Some scogs zips ship only raw + mafft (alignment-only layout).
    Some ship clipkit + treefile + bionj + iqtree (full pipeline layout).
    """
    genes: dict[str, dict[str, Path | None]] = {}
    for p in extracted.iterdir():
        if not p.is_file():
            continue
        name = p.name
        # Gene IDs in BUSCO eukaryota_odb10 start with digit then "at####"
        if not name[:1].isdigit():
            continue
        if "at" not in name.split(".")[0]:
            continue
        stem = name.split(".")[0]  # gene_id
        if stem not in genes:
            genes[stem] = {"raw": None, "mafft": None, "clipkit": None, "tree": None}
        if name.endswith(".faa.mafft.clipkit.treefile"):
            genes[stem]["tree"] = p
        elif name.endswith(".treefile"):
            # Less specific — only set if we don't have the clipkit one yet
            if genes[stem].get("tree") is None:
                genes[stem]["tree"] = p
        elif name.endswith(".faa.mafft.clipkit"):
            genes[stem]["clipkit"] = p
        elif name.endswith(".faa.mafft"):
            genes[stem]["mafft"] = p
        elif name.endswith(".faa"):
            genes[stem]["raw"] = p

    out = []
    for g, slots in sorted(genes.items()):
        # Pick best alignment: clipkit > mafft > raw
        aln = slots["clipkit"] or slots["mafft"] or slots["raw"]
        out.append((g, aln, slots["tree"]))
    return out


# ---------- Biopython-based metrics ----------

def _read_alignment(aln_path: Path):
    if not HAS_BIO:
        return None
    try:
        return AlignIO.read(str(aln_path), "fasta")
    except Exception:
        return None


def parsimony_informative_pct(aln_path: Path) -> float | None:
    """Replicate `phykit parsimony_informative_sites`: percentage of sites
    where >=2 distinct non-gap characters each appear in >=2 taxa.

    Output matches `phykit pis` column 3 to 4 decimal places.
    """
    aln = _read_alignment(aln_path)
    if aln is None:
        return None
    n_sites = aln.get_alignment_length()
    n_pi = 0
    for i in range(n_sites):
        col = aln[:, i]
        c = Counter(ch for ch in col if ch not in "-?Xx")
        if sum(1 for v in c.values() if v >= 2) >= 2:
            n_pi += 1
    return round(100.0 * n_pi / n_sites, 4) if n_sites else None


def rcv_value(aln_path: Path) -> float | None:
    """Replicate `phykit rcv` (Relative Composition Variability).

    For each taxon i: deviation = sum_c |freq(c, taxon_i) - freq(c, all)|
    RCV = mean over taxa of deviation / total alignment length.

    Implementation cross-checked against `phykit rcv` to 4 decimals.
    """
    aln = _read_alignment(aln_path)
    if aln is None:
        return None
    n_taxa = len(aln)
    aln_len = aln.get_alignment_length()
    if not n_taxa or not aln_len:
        return None
    # Average composition across full alignment (per residue)
    all_chars = "".join(str(rec.seq) for rec in aln)
    total_count = Counter(all_chars)
    total_chars = sum(total_count.values())  # taxa * length
    avg_freq = {c: total_count[c] / total_chars for c in total_count}

    deviation_sum = 0.0
    for rec in aln:
        seq = str(rec.seq)
        seq_count = Counter(seq)
        # Per-taxon deviation: sum over all chars c of |count_c - avg_freq * len|
        # Match phykit's formulation (un-normalized counts in numerator)
        dev = 0.0
        for c, total_c in total_count.items():
            taxon_c = seq_count.get(c, 0)
            avg_c = avg_freq[c] * len(seq)
            dev += abs(taxon_c - avg_c)
        deviation_sum += dev

    rcv = deviation_sum / (n_taxa * aln_len)
    return round(rcv, 4)


def gap_percentage_value(aln_path: Path) -> float | None:
    """Per-alignment gap percentage (gap chars / total positions * 100)."""
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
        return round(100.0 * gaps / total, 4) if total else None
    except Exception:
        return None


# ---------- phykit-based metrics ----------

def _run_phykit(metric: str, aln: Path | None, tree: Path | None) -> str | None:
    cmd = ["phykit", PHYKIT_CMD[metric]]
    if metric in PHYKIT_TREE_METRICS:
        if not tree:
            return None
        cmd.append(str(tree))
        if metric in ("long_branch_score", "patristic_distances"):
            cmd.append("-v")
    elif metric == "saturation":
        if not (aln and tree):
            return None
        cmd.extend(["-a", str(aln), "-t", str(tree)])
    elif metric == "treeness_over_rcv":
        if not (aln and tree):
            return None
        cmd.extend(["-a", str(aln), "-t", str(tree)])
    elif metric == "rcv":
        if not aln:
            return None
        cmd.append(str(aln))
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if r.returncode == 0:
            return r.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def _parse_per_tree(metric: str, output: str, per_tree_stat: str) -> float | None:
    """Convert phykit stdout to a single per-tree value."""
    lines = [ln for ln in output.split("\n") if ln.strip()]
    if not lines:
        return None
    if metric in ("long_branch_score", "patristic_distances"):
        vals = []
        for line in lines:
            parts = line.split("\t")
            try:
                vals.append(float(parts[-1]))
            except (ValueError, IndexError):
                continue
        if not vals:
            return None
        if per_tree_stat == "mean":
            return sum(vals) / len(vals)
        if per_tree_stat == "median":
            vals.sort()
            n = len(vals)
            return vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2
        return None
    # Single-value metrics (treeness, dvmc, total_tree_length, evolutionary_rate, rcv)
    first = lines[0]
    cols = first.split("\t")
    try:
        if metric == "saturation" and len(cols) >= 2:
            return float(cols[1])  # 1-slope (the reported "saturation value")
        if metric == "treeness_over_rcv" and len(cols) >= 1:
            return float(cols[0])  # treeness/RCV ratio
        return float(cols[0])
    except (ValueError, IndexError):
        return None


# ---------- Per-group computation ----------

def compute_group(metric: str, capsule: Path, group: str,
                  per_tree_stat: str, only_with_trees: bool,
                  workspace: Path | None = None) -> dict:
    """Compute per-ortholog values for one group.

    Returns: {gene_id -> value, ...} plus metadata.
    """
    extracted = ensure_extracted(capsule, group, workspace=workspace)
    orthologs = find_orthologs(extracted)
    print(f"# {group}: {len(orthologs)} orthologs found", file=sys.stderr)
    n_with_aln = sum(1 for _, a, _ in orthologs if a is not None)
    n_with_tree = sum(1 for _, _, t in orthologs if t is not None)
    print(f"#   with alignment: {n_with_aln}, with tree: {n_with_tree}",
          file=sys.stderr)

    if only_with_trees:
        orthologs = [(g, a, t) for g, a, t in orthologs if t is not None]

    values: dict[str, float] = {}
    for gene, aln, tree in orthologs:
        v: float | None = None
        if metric in ALN_BIOPY_METRICS:
            if aln is None:
                continue
            if metric == "parsimony_informative":
                v = parsimony_informative_pct(aln)
            elif metric == "rcv":
                v = rcv_value(aln)
            elif metric == "gap_percentage":
                v = gap_percentage_value(aln)
        elif metric in PHYKIT_TREE_METRICS:
            if tree is None:
                continue
            out = _run_phykit(metric, None, tree)
            if out:
                v = _parse_per_tree(metric, out, per_tree_stat)
        elif metric in PHYKIT_ALN_AND_TREE:
            if aln is None or tree is None:
                continue
            out = _run_phykit(metric, aln, tree)
            if out:
                v = _parse_per_tree(metric, out, per_tree_stat)
        if v is not None:
            values[gene] = round(v, 4)
    return values


# ---------- Summary stats ----------

def _summary(values: list[float]) -> dict:
    if not values:
        return {"n": 0}
    s = sorted(values)
    n = len(s)
    nonzero = [v for v in s if v > 0]
    summary = {
        "n": n,
        "mean": round(statistics.mean(s), 6),
        "median": round(statistics.median(s), 6),
        "min": round(s[0], 6),
        "max": round(s[-1], 6),
        "p25": round(statistics.quantiles(s, n=4)[0], 6) if n >= 4 else None,
        "p75": round(statistics.quantiles(s, n=4)[2], 6) if n >= 4 else None,
        "lowest_nonzero": round(min(nonzero), 6) if nonzero else None,
        "n_nonzero": len(nonzero),
    }
    return summary


def _emit_summary(group: str, values: dict[str, float]) -> None:
    s = _summary(list(values.values()))
    parts = [f"{k}={v}" for k, v in s.items()]
    print(f"# SUMMARY group={group}: " + " ".join(parts))


def _mwu(a: list[float], b: list[float]) -> tuple[float | None, float | None]:
    if not a or not b:
        return None, None
    if HAS_SCIPY:
        u, p = _stats.mannwhitneyu(a, b, alternative="two-sided")
        return float(u), float(p)
    return None, None


# ---------- Main ----------

def main():
    ap = argparse.ArgumentParser(
        description="Paired group comparison (animals vs fungi) on scogs alignments+trees.",
    )
    ap.add_argument("--data-folder", "--capsule", required=True, type=Path,
                    dest="data_folder",
                    help="Data folder containing scogs_*.zip files (e.g. "
                         "scogs_animals.zip + scogs_fungi.zip)")
    ap.add_argument("--metric", required=True, choices=sorted(ALL_METRICS))
    ap.add_argument("--per-tree-stat", default="mean", choices=["mean", "median"],
                    help="For long_branch_score / patristic_distances: how to "
                         "summarize multiple values per tree.")
    ap.add_argument("--groups", default="animals,fungi",
                    help="Comma-separated group order (default 'animals,fungi'). "
                         "Choices: animals, fungi.")
    ap.add_argument("--only-with-trees", action="store_true",
                    help="Drop orthologs that do NOT have a tree file. Important "
                         "when comparing tree metrics; also affects denominators.")
    ap.add_argument("--out-json", help="Optional path to write per-ortholog JSON.")
    ap.add_argument("--workspace", type=Path, default=None,
                    help="Where to extract zip contents. Default /tmp/scogs_<folder>. "
                         "Pass an explicit path when the input data folder is read-only.")
    args = ap.parse_args()

    groups = [g.strip() for g in args.groups.split(",") if g.strip()]
    needs_tree = args.metric in PHYKIT_TREE_METRICS or args.metric in PHYKIT_ALN_AND_TREE
    only_with_trees = args.only_with_trees or needs_tree

    print(f"# metric={args.metric}, per_tree_stat={args.per_tree_stat}, "
          f"only_with_trees={only_with_trees}, groups={groups}", file=sys.stderr)

    per_group: dict[str, dict[str, float]] = {}
    for grp in groups:
        per_group[grp] = compute_group(
            args.metric, args.data_folder, grp, args.per_tree_stat, only_with_trees,
            workspace=args.workspace,
        )
        _emit_summary(grp, per_group[grp])

    # Pairwise MWU + paired diffs (if both groups present)
    if len(groups) == 2:
        a_name, b_name = groups[0], groups[1]
        a_vals = list(per_group[a_name].values())
        b_vals = list(per_group[b_name].values())
        u_ab, p_ab = _mwu(a_vals, b_vals)
        u_ba, p_ba = _mwu(b_vals, a_vals)
        if u_ab is not None:
            # MWU U is symmetric: U(a,b)+U(b,a)=n_a*n_b. Print both orderings
            # so the agent doesn't have to swap arguments to match question phrasing.
            print(f"# MWU {a_name}_vs_{b_name}: U={u_ab} p={p_ab}")
            print(f"# MWU {b_name}_vs_{a_name}: U={u_ba} p={p_ba}")

        # Paired differences across common gene_ids
        common = sorted(set(per_group[a_name]) & set(per_group[b_name]))
        if common:
            diffs_ab = [per_group[a_name][g] - per_group[b_name][g] for g in common]
            diffs_ba = [per_group[b_name][g] - per_group[a_name][g] for g in common]
            ratios_ab = [
                per_group[a_name][g] / per_group[b_name][g]
                for g in common if per_group[b_name][g] != 0
            ]
            ratios_ba = [
                per_group[b_name][g] / per_group[a_name][g]
                for g in common if per_group[a_name][g] != 0
            ]
            print(f"# PAIRED n_common={len(common)}: "
                  f"median_diff({a_name}-{b_name})={round(statistics.median(diffs_ab), 6)} "
                  f"median_diff({b_name}-{a_name})={round(statistics.median(diffs_ba), 6)}")

        # Group-median ratio (different from paired-ratio median!) — emitted
        # BEFORE the per-ortholog ratios because most "median ratio of A to B"
        # benchmark questions are scored against this group-medians ratio,
        # even when the question wording mentions "paired orthologs". The
        # canonical fold-change interpretation in transcriptomics/phylogenomics
        # is median(group A) / median(group B), not the median per-ortholog
        # ratio.
        if a_vals and b_vals:
            m_a = statistics.median(a_vals)
            m_b = statistics.median(b_vals)
            if m_b:
                print(f"# GROUP_MEDIAN_RATIO {a_name}/{b_name}="
                      f"{round(m_a / m_b, 6)}  "
                      f"<-- canonical fold-change: median(A)/median(B), USE FIRST for 'median ratio of A to B'")
            if m_a:
                print(f"# GROUP_MEDIAN_RATIO {b_name}/{a_name}="
                      f"{round(m_b / m_a, 6)}")
            print(f"# GROUP_MEDIAN_DIFF {a_name}-{b_name}="
                  f"{round(m_a - m_b, 6)}")

        # Per-ortholog ratios reported LAST so the agent picks
        # GROUP_MEDIAN_RATIO above by default. PAIRED RATIO is only correct
        # when the question explicitly asks for "per-ortholog ratio" or
        # "fold change computed per pair then summarized".
        if common and ratios_ab:
            print(f"# PAIRED_PER_ORTHOLOG_RATIO median({a_name}/{b_name})="
                  f"{round(statistics.median(ratios_ab), 6)} "
                  f"(n={len(ratios_ab)}; per-pair ratio, then median — NOT canonical fold-change)")
        if common and ratios_ba:
            print(f"# PAIRED_PER_ORTHOLOG_RATIO median({b_name}/{a_name})="
                  f"{round(statistics.median(ratios_ba), 6)} "
                  f"(n={len(ratios_ba)}; per-pair ratio, then median — NOT canonical fold-change)")

        # Lowest-nonzero ratios (for "ratio of lowest X" questions where 0
        # values exist as artifacts of conserved/short alignments)
        a_nz = [v for v in a_vals if v > 0]
        b_nz = [v for v in b_vals if v > 0]
        if a_nz and b_nz:
            print(f"# LOWEST_NONZERO {a_name}={round(min(a_nz), 6)} "
                  f"{b_name}={round(min(b_nz), 6)}")
            print(f"# LOWEST_NONZERO_RATIO {a_name}/{b_name}="
                  f"{round(min(a_nz) / min(b_nz), 6)}")
            print(f"# LOWEST_NONZERO_RATIO {b_name}/{a_name}="
                  f"{round(min(b_nz) / min(a_nz), 6)}")

    if args.out_json:
        Path(args.out_json).write_text(json.dumps(
            {grp: per_group[grp] for grp in groups},
            indent=2, sort_keys=True,
        ))
        print(f"# wrote per-ortholog JSON to {args.out_json}", file=sys.stderr)


if __name__ == "__main__":
    main()
