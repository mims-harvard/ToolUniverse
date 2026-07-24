#!/usr/bin/env python3
"""Per-condition enrichment screen — run enrichment across N conditions
and report what fraction had any significant hit (optionally filtered by
a keyword/category). Built for "% of conditions with significant
enrichment of <category> pathways" questions.

Why this exists:
- The agent kept timing out trying to enumerate conditions one-by-one.
  This script accepts either:
    (a) a 2-col TSV of `condition_label<TAB>gene` for ALL conditions;
        groups by condition and runs enrichr per group.
    (b) multiple --condition-genes <label>=<file.txt> args (one per
        condition).
- Outputs per-condition summaries and a final aggregate percentage.
- The "category filter" lets the user say "count a condition as
  positive only if at least one significant term matches keyword X"
  (e.g., "immune", "Oxidative", "stress").

Usage:

    # (a) Single TSV with all conditions:
    python condition_enrichment_screen.py \\
        --conditions-tsv /tmp/all_conds.tsv \\
        --library ReactomePathways.gmt \\
        --background /tmp/expressed.txt \\
        --exclude-condition no_T_cells \\
        --keyword immune --keyword interferon --keyword cytokine \\
        --workdir /tmp/cond_screen

    # (b) Per-condition gene-list files:
    python condition_enrichment_screen.py \\
        --condition-genes acute=/tmp/acute_sig.txt \\
        --condition-genes round1=/tmp/r1_sig.txt \\
        --condition-genes round2=/tmp/r2_sig.txt \\
        --condition-genes round3=/tmp/r3_sig.txt \\
        --library ReactomePathways.gmt \\
        --background /tmp/expressed.txt \\
        --keyword "immune" --keyword "interferon" \\
        --workdir /tmp/cond_screen

Output blocks (parseable):
    # CONDITION acute: n_genes=234 sig_terms=0 sig_terms_keyword=0  POSITIVE=False
    # CONDITION round1: n_genes=189 sig_terms=4 sig_terms_keyword=2  POSITIVE=True
    # CONDITION round2: ...
    # SUMMARY: n_conditions_total=4 n_excluded=0 n_evaluated=4
    #           n_with_any_sig=2 pct_with_any_sig=50.00%
    #           n_with_keyword_sig=2 pct_with_keyword_sig=50.00%
    # KEYWORDS used: ['immune', 'interferon']

WORKSPACE ISOLATION
-------------------
This script writes only to --workdir. NEVER writes to the input dir.

Notes:
- The library can be either an Enrichr library name (e.g.
  KEGG_2021_Human, Reactome_2022) OR a path to a local .gmt file.
- "Sig" means Adjusted P-value < --padj-cutoff (default 0.05).
- "Keyword match" is case-insensitive substring on the Term column.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path


def _read_gene_list(path: Path) -> list[str]:
    raw = [ln.strip() for ln in path.read_text().splitlines() if ln.strip()]
    if not raw:
        return []
    first = raw[0].lower()
    if first in ("gene", "symbol", "gene_symbol", "gene_name", "gene_id", "id"):
        raw = raw[1:]
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


def _read_conditions_tsv(path: Path) -> dict[str, list[str]]:
    """Parse a 2-col TSV: condition<TAB>gene. Returns {condition: [genes]}."""
    out: dict[str, list[str]] = {}
    raw = [ln.strip() for ln in path.read_text().splitlines() if ln.strip()]
    if not raw:
        return out
    # Skip header if present
    first = raw[0].lower()
    if "\t" in raw[0]:
        toks = raw[0].split("\t")
        if any(tok.lower() in ("condition", "label", "screen", "round", "treatment") for tok in toks):
            raw = raw[1:]
    for ln in raw:
        if "\t" not in ln:
            continue
        cond, gene = ln.split("\t", 1)
        cond = cond.strip().strip('"')
        gene = gene.strip().strip('"').split("\t")[0]
        if not cond or not gene:
            continue
        out.setdefault(cond, []).append(gene)
    return out


def _parse_condition_genes(args_list: list[str]) -> dict[str, list[str]]:
    """Parse --condition-genes label=path/to.txt args into dict."""
    out: dict[str, list[str]] = {}
    for arg in args_list:
        if "=" not in arg:
            sys.exit(f"ERROR: --condition-genes must be 'label=path', got '{arg}'")
        label, path_s = arg.split("=", 1)
        out[label.strip()] = _read_gene_list(Path(path_s.strip()))
    return out


def _is_local_gmt(library: str) -> bool:
    return library.endswith(".gmt") and Path(library).exists()


def _load_library(library: str):
    """Return either the library name (string) for Enrichr, or a parsed
    {set_name: [gene1, ...]} dict for a local .gmt file.
    """
    if _is_local_gmt(library):
        d = {}
        with open(library) as f:
            for ln in f:
                parts = ln.rstrip("\n").split("\t")
                if len(parts) < 3:
                    continue
                name = parts[0].strip()
                # parts[1] is description (often empty), rest are genes
                genes = [g.strip() for g in parts[2:] if g.strip()]
                if name and genes:
                    d[name] = genes
        return d
    return library


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--conditions-tsv",
                     help="2-col TSV: condition<TAB>gene (multiple genes per condition).")
    src.add_argument("--condition-genes", action="append", default=[],
                     help="label=path/to/gene_list.txt. Repeatable.")
    ap.add_argument("--library", required=True,
                    help="Enrichr library name OR path to local .gmt.")
    ap.add_argument("--organism", default="Human",
                    help="Enrichr organism (only used for online libraries).")
    ap.add_argument("--background",
                    help="Background gene-list file (one per line).")
    ap.add_argument("--padj-cutoff", type=float, default=0.05,
                    help="Adjusted P-value cutoff for 'significant' (default 0.05).")
    ap.add_argument("--keyword", action="append", default=[],
                    help="Keyword(s) to filter terms — a condition is "
                         "category-positive iff any sig term contains a keyword. "
                         "Repeatable, case-insensitive.")
    ap.add_argument("--exclude-condition", action="append", default=[],
                    help="Skip this condition label (e.g. 'no_T_cells_control'). "
                         "Repeatable.")
    ap.add_argument("--workdir", default="",
                    help="Output dir.")
    args = ap.parse_args()

    if args.workdir:
        workdir = Path(args.workdir).resolve()
    else:
        workdir = Path(tempfile.mkdtemp(prefix="cond_screen_"))
    workdir.mkdir(parents=True, exist_ok=True)
    print(f"# workdir: {workdir}", file=sys.stderr)

    # Build the conditions dict
    if args.conditions_tsv:
        conds = _read_conditions_tsv(Path(args.conditions_tsv))
    else:
        conds = _parse_condition_genes(args.condition_genes or [])

    if not conds:
        sys.exit("ERROR: no conditions parsed.")

    # Background
    bg = None
    if args.background:
        bg = _read_gene_list(Path(args.background))
        print(f"# background: n={len(bg)}", file=sys.stderr)

    # Library
    library = _load_library(args.library)
    is_dict_lib = isinstance(library, dict)
    if is_dict_lib:
        print(f"# library: local GMT {args.library} ({len(library)} sets)", file=sys.stderr)
    else:
        print(f"# library: {library} (Enrichr)", file=sys.stderr)

    # Run per-condition
    import gseapy as gp

    excluded_set = set(args.exclude_condition or [])
    keywords = [k.lower() for k in (args.keyword or [])]

    n_evaluated = 0
    n_with_any_sig = 0
    n_with_keyword_sig = 0
    excluded_seen = []

    # Throttle Enrichr requests — its public API rate-limits aggressively.
    import time
    enrichr_throttle_s = 1.5

    for label in sorted(conds.keys()):
        if label in excluded_set:
            excluded_seen.append(label)
            print(f"# CONDITION {label}: EXCLUDED")
            continue
        genes = conds[label]
        if not genes:
            print(f"# CONDITION {label}: n_genes=0 (skipping)")
            continue
        n_evaluated += 1

        # Retry up to 3x on transient Enrichr errors (rate limits, 5xx)
        res = None
        last_err = None
        for attempt in range(3):
            try:
                if is_dict_lib:
                    # gp.enrich (offline GMT) — does NOT accept organism arg
                    res = gp.enrich(
                        gene_list=genes,
                        gene_sets=library,
                        background=bg,
                        outdir=None,
                        no_plot=True,
                    )
                else:
                    # gp.enrichr (online) — needs organism
                    kwargs = dict(
                        outdir=None,
                        no_plot=True,
                        organism=args.organism,
                        gene_sets=library,
                    )
                    if bg is not None:
                        kwargs["background"] = bg
                    res = gp.enrichr(gene_list=genes, **kwargs)
                break
            except Exception as e:
                last_err = e
                msg = str(e).lower()
                if "429" in msg or "503" in msg or "504" in msg or "timeout" in msg:
                    backoff = (attempt + 1) * 5.0
                    print(f"# CONDITION {label}: transient ({type(e).__name__}), "
                          f"retry in {backoff}s ({attempt + 1}/3)")
                    time.sleep(backoff)
                    continue
                # Non-transient error — give up on this condition
                break
        if res is None:
            print(f"# CONDITION {label}: ERROR {type(last_err).__name__ if last_err else 'unknown'}: {last_err}")
            continue
        # Per-call throttle
        if not is_dict_lib:
            time.sleep(enrichr_throttle_s)

        df = res.results
        if df is None or len(df) == 0:
            print(f"# CONDITION {label}: n_genes={len(genes)} no_terms_returned")
            continue

        sig = df[df["Adjusted P-value"] < args.padj_cutoff]
        n_sig = len(sig)
        if keywords and n_sig > 0:
            terms_lower = sig["Term"].astype(str).str.lower()
            mask = terms_lower.apply(lambda t: any(k in t for k in keywords))
            n_kw_sig = int(mask.sum())
        else:
            n_kw_sig = 0

        any_pos = n_sig > 0
        kw_pos = n_kw_sig > 0
        if any_pos:
            n_with_any_sig += 1
        if kw_pos or (not keywords and any_pos):
            # If no keywords given, "category positive" is just "any sig"
            n_with_keyword_sig += 1

        print(f"# CONDITION {label}: n_genes={len(genes)} "
              f"sig_terms={n_sig} sig_terms_keyword={n_kw_sig} "
              f"ANY_POSITIVE={any_pos} KEYWORD_POSITIVE={kw_pos}")

        # Save full result
        out = workdir / f"cond_{label.replace('/', '_')}.csv"
        df.sort_values(by="Adjusted P-value", ascending=True).to_csv(out, index=False)

    print()
    print("# === SUMMARY ===")
    print(f"# n_conditions_total={len(conds)} n_excluded={len(excluded_seen)} "
          f"n_evaluated={n_evaluated}")
    if n_evaluated == 0:
        print("# No conditions evaluated — cannot compute percentages.")
        return

    pct_any = 100.0 * n_with_any_sig / n_evaluated
    pct_kw = 100.0 * n_with_keyword_sig / n_evaluated
    print(f"# n_with_any_sig={n_with_any_sig} pct_with_any_sig={pct_any:.2f}%")
    if keywords:
        print(f"# n_with_keyword_sig={n_with_keyword_sig} "
              f"pct_with_keyword_sig={pct_kw:.2f}%")
        print(f"# KEYWORDS used: {args.keyword}")
    if excluded_seen:
        print(f"# EXCLUDED: {excluded_seen}")
    print("# DONE")


if __name__ == "__main__":
    main()
