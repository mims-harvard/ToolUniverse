#!/usr/bin/env python3
"""Deterministic gseapy enrichr / prerank runner.

Why this exists:
- Enrichment top hits depend critically on three things the agent rarely
  controls explicitly: (a) the upstream DEG/gene-list filter, (b) the
  Enrichr library snapshot (libraries get republished), and (c) how ties
  on Adjusted P-value are broken. This script makes ALL THREE visible.
- Many published RNA-seq notebooks sort the enrichr result by Adjusted
  P-value ascending and take the first row, so the answer is whichever
  row pandas places first given the index order Enrichr returned. That
  tie-break is fragile, so this script reports BOTH the raw top-by-
  adj-pvalue AND a deterministic tie-broken top (adj-p, then raw-p,
  then overlap_count desc, then term alphabetic). It also reports the
  rank of any candidate term the user passes via --candidate.

Usage examples:

    # Single library on a gene-list file (one gene per line, header optional):
    python gseapy_enrichment_runner.py \\
        --gene-list /tmp/cbd_combo_degs.txt \\
        --library GO_Biological_Process_2021 \\
        --organism Human \\
        --top 5

    # Multiple libraries + custom background + report rank of candidates:
    python gseapy_enrichment_runner.py \\
        --gene-list /tmp/sig.txt \\
        --library WikiPathways_2019_Mouse,KEGG_2019_Mouse \\
        --organism Mouse \\
        --background /tmp/expressed.txt \\
        --candidate "Oxidative Stress" --candidate "Glutathione metabolism"

    # GSEA preranked: provide gene -> score TSV, runs gp.prerank
    python gseapy_enrichment_runner.py \\
        --ranked-list /tmp/ranked.tsv --library GO_Biological_Process_2021 \\
        --mode prerank

Output blocks (parseable):
    # LIBRARY <name>: total_terms=N significant_padj<0.05=K
    # TOP_BY_ADJ_PVALUE: <term-as-returned-by-pandas-sort>
    # TOP_TIE_BROKEN: <term-after-deterministic-tie-break>
    # TOP5_BY_ADJ_PVALUE:
    #   1. <term> | adj_p=... raw_p=... overlap=a/b genes=...
    #   2. ...
    # CANDIDATE_RANK <term>: rank=R adj_p=... raw_p=... overlap=a/b
    # TIES_AT_TOP: n=K  (number of rows tied at the lowest Adjusted P-value)
    # WARNING: top adj_p tied across N terms — see TOP5 listing.

WORKSPACE ISOLATION
-------------------
This script writes only to --workdir (default $TMPDIR/gseapy_run_<pid>).
It NEVER writes to the gene-list directory. Pass --workdir /tmp/... to
keep canonical data folders read-only.
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path


def _read_gene_list(path: Path) -> list[str]:
    """Read a gene list file. Accepts plain (one per line), CSV, or TSV.

    Skips header row if first non-blank line looks like a header (contains
    no digits AND has known header words like 'gene', 'symbol', 'name').
    """
    raw = [ln.strip() for ln in path.read_text().splitlines() if ln.strip()]
    if not raw:
        return []
    # Detect header
    first = raw[0].lower()
    if any(tok in first for tok in ("gene", "symbol", "name", "id")) and not any(
        ch.isdigit() for ch in first.split()[0]
    ):
        # Could be header — skip if its 1st token is non-numeric and contains gene/etc.
        # but only if it's really not a gene name
        if first in ("gene", "symbol", "gene_symbol", "gene_name", "gene_id", "symbols", "id"):
            raw = raw[1:]
    # If lines look like CSV/TSV, take first column
    out = []
    for ln in raw:
        if "\t" in ln:
            ln = ln.split("\t")[0]
        elif "," in ln:
            ln = ln.split(",")[0]
        ln = ln.strip().strip('"').strip("'")
        if ln:
            out.append(ln)
    return out


def _read_ranked_list(path: Path) -> list[tuple[str, float]]:
    """Read a 2-col gene+score TSV/CSV. Skips obvious header."""
    pairs: list[tuple[str, float]] = []
    raw = [ln.strip() for ln in path.read_text().splitlines() if ln.strip()]
    for i, ln in enumerate(raw):
        if "\t" in ln:
            parts = ln.split("\t")
        elif "," in ln:
            parts = ln.split(",")
        else:
            parts = ln.split()
        if len(parts) < 2:
            continue
        gene = parts[0].strip().strip('"').strip("'")
        try:
            score = float(parts[1])
        except ValueError:
            if i == 0:
                continue  # header
            continue
        pairs.append((gene, score))
    return pairs


def _parse_overlap(s) -> int:
    """gseapy's Overlap column is like '7/124'. Return numerator as int."""
    try:
        return int(str(s).split("/")[0])
    except Exception:
        return 0


def _print_top_block(df, header: str, top: int) -> None:
    print(header)
    for i, (_, row) in enumerate(df.head(top).iterrows(), 1):
        term = row.get("Term", "?")
        adj = row.get("Adjusted P-value", float("nan"))
        raw = row.get("P-value", float("nan"))
        overlap = row.get("Overlap", "?")
        genes = row.get("Genes", "")
        if isinstance(genes, str) and len(genes) > 80:
            genes = genes[:77] + "..."
        print(f"#   {i}. {term} | adj_p={adj:.4g} raw_p={raw:.4g} overlap={overlap} genes={genes}")


def run_enrichr(args, gene_list: list[str], background: list[str] | None) -> None:
    import gseapy as gp

    libraries = [lib.strip() for lib in args.library.split(",") if lib.strip()]

    # Run each library separately so results never get mixed up by gseapy's
    # batched Gene_set column. (gp.enrichr accepts a list, but we want
    # explicit per-library reporting.)
    for lib in libraries:
        print(f"\n# === LIBRARY {lib} ===", flush=True)
        try:
            kwargs = dict(
                gene_list=gene_list,
                gene_sets=lib,
                organism=args.organism,
                outdir=None,
                no_plot=True,
            )
            if background is not None:
                kwargs["background"] = background
            if args.cutoff is not None:
                kwargs["cutoff"] = args.cutoff
            res = gp.enrichr(**kwargs)
        except Exception as e:
            print(f"# ERROR running enrichr on {lib}: {type(e).__name__}: {e}")
            continue

        df = res.results
        if df is None or len(df) == 0:
            print(f"# LIBRARY {lib}: no terms returned (gene list possibly all unmapped)")
            continue

        # Sort by adjusted p-value asc — this is what published notebooks do.
        df_sorted = df.sort_values(by="Adjusted P-value", ascending=True, kind="mergesort")
        n_sig = int((df_sorted["Adjusted P-value"] < 0.05).sum())
        print(f"# LIBRARY {lib}: total_terms={len(df_sorted)} significant_padj<0.05={n_sig}")

        # The "top by Adjusted P-value" — what `df.sort_values(...).iloc[0]` returns.
        top_row = df_sorted.iloc[0]
        top_adj = top_row["Adjusted P-value"]
        ties_at_top = int((df_sorted["Adjusted P-value"] == top_adj).sum())
        print(f"# TOP_BY_ADJ_PVALUE: {top_row['Term']}")
        print(f"# TIES_AT_TOP: n={ties_at_top}")
        if ties_at_top > 1:
            print(f"# WARNING: top adj_p tied across {ties_at_top} terms — published "
                  f"answers may pick any of them by raw P-value, by overlap, or by "
                  f"alphabetical order. See the TOP{max(args.top, ties_at_top)} listing below.")

        # Deterministic tie break: adj_p asc, raw_p asc, overlap desc, term alphabetic
        df_tb = df_sorted.copy()
        df_tb["__overlap_n"] = df_tb["Overlap"].map(_parse_overlap)
        df_tb = df_tb.sort_values(
            by=["Adjusted P-value", "P-value", "__overlap_n", "Term"],
            ascending=[True, True, False, True],
            kind="mergesort",
        )
        top_tb = df_tb.iloc[0]
        print(f"# TOP_TIE_BROKEN: {top_tb['Term']}")

        # Top N by adj_p (raw, no extra tiebreak — same order as the notebook).
        # If ties at top exceed args.top, expand to show ALL tied terms so the
        # agent can match the published answer.
        n_show = max(args.top, ties_at_top)
        _print_top_block(df_sorted, f"# TOP{n_show}_BY_ADJ_PVALUE:", n_show)

        # Candidate ranks: report each candidate's position in the
        # adj-p-sorted frame. Substring match (case-insensitive, gseapy
        # appends "(GO:NNNN)" so substring is more reliable than exact).
        if args.candidate:
            for cand in args.candidate:
                cand_l = cand.lower()
                matches = df_sorted[df_sorted["Term"].str.lower().str.contains(
                    cand_l, regex=False
                )]
                if len(matches) == 0:
                    print(f"# CANDIDATE_RANK '{cand}': not found in {lib}")
                    continue
                # Pick first hit; report its rank in the adj-p-sorted frame.
                first_idx = df_sorted.index.get_loc(matches.index[0])
                row = matches.iloc[0]
                print(
                    f"# CANDIDATE_RANK '{cand}': rank={first_idx + 1} "
                    f"adj_p={row['Adjusted P-value']:.4g} "
                    f"raw_p={row['P-value']:.4g} overlap={row['Overlap']} "
                    f"matched_term=\"{row['Term']}\""
                )

        # Optional: substring counter ("How many top-N terms contain X")
        if args.count_substring:
            for sub in args.count_substring:
                sub_l = sub.lower()
                topN_terms = df_sorted.head(args.top_n_count)["Term"].astype(str).str.lower()
                hits = int(topN_terms.str.contains(sub_l, regex=False).sum())
                print(f"# SUBSTRING_COUNT_TOP{args.top_n_count} '{sub}': {hits}")

        # Save per-library full table to workdir
        out_path = Path(args.workdir) / f"enrichr_{lib.replace('/', '_')}.csv"
        df_sorted.to_csv(out_path, index=False)
        print(f"# wrote full table: {out_path}")


def run_prerank(args, ranked: list[tuple[str, float]]) -> None:
    import gseapy as gp
    import pandas as pd

    libraries = [lib.strip() for lib in args.library.split(",") if lib.strip()]
    rnk = pd.DataFrame(ranked, columns=["gene", "score"]).set_index("gene")["score"]
    rnk = rnk[~rnk.index.duplicated(keep="first")].sort_values(ascending=False)

    for lib in libraries:
        print(f"\n# === GSEA LIBRARY {lib} ===", flush=True)
        try:
            res = gp.prerank(
                rnk=rnk,
                gene_sets=lib,
                outdir=None,
                no_plot=True,
                permutation_num=args.permutations,
                seed=42,
                threads=1,
                min_size=5,
                max_size=2000,
            )
        except Exception as e:
            print(f"# ERROR running prerank on {lib}: {type(e).__name__}: {e}")
            continue

        df = res.res2d
        if df is None or len(df) == 0:
            print(f"# GSEA LIBRARY {lib}: no terms returned")
            continue

        # FDR q-val sort
        df_sorted = df.sort_values(by="FDR q-val", ascending=True, kind="mergesort")
        n_sig = int((df_sorted["FDR q-val"].astype(float) < 0.25).sum())
        print(f"# GSEA LIBRARY {lib}: total={len(df_sorted)} sig_FDR<0.25={n_sig}")
        top = df_sorted.iloc[0]
        print(f"# GSEA TOP_BY_FDR: {top.get('Term', '?')} NES={top.get('NES','?')} FDR={top.get('FDR q-val','?')}")
        print(f"# GSEA TOP{args.top}_BY_FDR:")
        for i, (_, row) in enumerate(df_sorted.head(args.top).iterrows(), 1):
            print(
                f"#   {i}. {row.get('Term','?')} | NES={row.get('NES','?')} "
                f"FDR={row.get('FDR q-val','?')} NOM={row.get('NOM p-val','?')} "
                f"lead_genes={str(row.get('Lead_genes',''))[:60]}"
            )

        out_path = Path(args.workdir) / f"prerank_{lib.replace('/', '_')}.csv"
        df_sorted.to_csv(out_path, index=False)
        print(f"# wrote full table: {out_path}")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--mode", default="enrichr", choices=["enrichr", "prerank"],
                    help="enrichr=ORA, prerank=GSEA preranked. Default enrichr.")
    ap.add_argument("--gene-list", help="One gene per line (or CSV/TSV; first col taken). Required for enrichr mode.")
    ap.add_argument("--ranked-list", help="2-col TSV/CSV (gene, score). Required for prerank mode.")
    ap.add_argument("--library", required=True,
                    help="Comma-sep Enrichr library name(s), e.g. "
                         "GO_Biological_Process_2021,KEGG_2021_Human")
    ap.add_argument("--organism", default="Human",
                    help="Enrichr organism. One of Human/Mouse/Rat/Fly/Worm/Yeast/Fish.")
    ap.add_argument("--background", default=None,
                    help="Optional background gene-list file (one per line).")
    ap.add_argument("--cutoff", type=float, default=None,
                    help="gseapy 'cutoff' param (default 0.05). Filters significant only.")
    ap.add_argument("--top", type=int, default=5,
                    help="How many top terms to print per library (default 5).")
    ap.add_argument("--candidate", action="append", default=[],
                    help="Candidate term name (substring) to report rank for. Repeatable.")
    ap.add_argument("--count-substring", action="append", default=[],
                    help="Count occurrences of this substring in top-N terms. Repeatable.")
    ap.add_argument("--top-n-count", type=int, default=20,
                    help="Top-N for --count-substring (default 20).")
    ap.add_argument("--permutations", type=int, default=1000,
                    help="GSEA permutation count (prerank mode only).")
    ap.add_argument("--workdir", default="",
                    help="Output dir (default $TMPDIR/gseapy_run_<pid>). NEVER writes "
                         "into the gene-list directory.")
    args = ap.parse_args()

    if args.workdir:
        workdir = Path(args.workdir).resolve()
    else:
        workdir = Path(tempfile.mkdtemp(prefix="gseapy_run_"))
    workdir.mkdir(parents=True, exist_ok=True)
    args.workdir = str(workdir)
    print(f"# workdir: {workdir}", file=sys.stderr)

    # Refuse to write inside a the input data folder directory (canonical data folders
    # are read-only). Allow tmp directories.
    workdir_r = workdir.resolve()
    for src in (args.gene_list, args.ranked_list, args.background):
        if not src:
            continue
        input_dir = Path(src).resolve().parent
        if workdir_r == input_dir or input_dir in workdir_r.parents:
            sys.exit(
                f"ERROR: workdir {workdir} is inside the input data folder "
                f"{input_dir}. Use --workdir /tmp/... to keep input data read-only."
            )

    if args.mode == "enrichr":
        if not args.gene_list:
            sys.exit("ERROR: --gene-list required for enrichr mode.")
        genes = _read_gene_list(Path(args.gene_list))
        print(f"# gene_list: n={len(genes)} (first 5: {genes[:5]})", file=sys.stderr)
        if not genes:
            sys.exit("ERROR: gene list is empty.")
        bg = None
        if args.background:
            bg = _read_gene_list(Path(args.background))
            print(f"# background: n={len(bg)}", file=sys.stderr)
        run_enrichr(args, genes, bg)
    else:
        if not args.ranked_list:
            sys.exit("ERROR: --ranked-list required for prerank mode.")
        ranked = _read_ranked_list(Path(args.ranked_list))
        print(f"# ranked_list: n={len(ranked)}", file=sys.stderr)
        if not ranked:
            sys.exit("ERROR: ranked list is empty.")
        run_prerank(args, ranked)

    print("\n# DONE", flush=True)


if __name__ == "__main__":
    main()
