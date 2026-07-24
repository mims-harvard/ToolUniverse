#!/usr/bin/env python3
"""Compute multi-condition Venn-style overlaps from DEG-list CSV files.

Why this exists:
- "% of genes DE in A AND DE in B AND NOT in any other strain" is highly
  ambiguous: which strains count as "other"? Which denominator? With or
  without LFC threshold?
- This script takes one or more DEG-list CSVs (one per condition) and
  emits ALL relevant overlap and percentage interpretations.

Usage:
    # If you've already run DESeq2 and saved per-contrast results CSVs:
    python multi_strain_venn.py \\
        --deg-csv "JBX97=res_unshrunk_Strain_97_vs_1.csv" \\
        --deg-csv "JBX98=res_unshrunk_Strain_98_vs_1.csv" \\
        --deg-csv "JBX99=res_unshrunk_Strain_99_vs_1.csv" \\
        --padj-thr 0.05 --lfc-thr 1.5 --basemean-thr 0 \\
        --target-set "JBX97,JBX99" \\
        --denominators "JBX97,JBX99,intersect,union,target_intersect"

    # Or if you just have plain gene-list .txt files (one gene per line):
    python multi_strain_venn.py \\
        --gene-list "JBX97=jbx97_sigs.txt" \\
        --gene-list "JBX99=jbx99_sigs.txt" \\
        --gene-list "JBX98=jbx98_sigs.txt" \\
        --target-set "JBX97,JBX99"

Output (parseable):
    # SET <name>: n=...
    # NUMERATOR target_intersect_minus_others = ...  (target sets ∩, then setdiff with all OTHER labels)
    # PCT numerator / |target_set[0]| = ...%
    # PCT numerator / |union_of_targets| = ...%
    # PCT numerator / |union_of_all| = ...%
    # PCT numerator / |intersect_of_targets| = ...%
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd


def parse_kv(arg: str) -> tuple[str, str]:
    if "=" not in arg:
        sys.exit(f"ERROR: '{arg}' must be of the form LABEL=PATH")
    label, path = arg.split("=", 1)
    return label.strip(), path.strip()


def gene_set_from_csv(path: str, padj_thr: float, lfc_thr: float, basemean_thr: float,
                      gene_col: str | None = None) -> set[str]:
    """Read a DESeq2 results CSV and return the set of significant gene names."""
    df = pd.read_csv(path, index_col=0)
    needed_cols = {"padj", "log2FoldChange", "baseMean"}
    missing = needed_cols - set(df.columns)
    if missing:
        sys.exit(f"ERROR: {path} missing columns: {missing}. "
                 f"Found columns: {list(df.columns)}")
    sig = df[
        df["padj"].notna()
        & (df["padj"] < padj_thr)
        & (df["log2FoldChange"].abs() > lfc_thr)
        & (df["baseMean"] > basemean_thr)
    ]
    if gene_col and gene_col in sig.columns:
        return set(sig[gene_col].astype(str))
    return set(sig.index.astype(str))


def gene_set_from_txt(path: str) -> set[str]:
    return {line.strip() for line in Path(path).read_text().splitlines()
            if line.strip() and not line.startswith("#")}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--deg-csv", action="append", default=[],
                    help="LABEL=PATH for a DESeq2 results CSV. Can repeat. "
                         "Sig set = padj<thr AND |LFC|>thr AND baseMean>thr.")
    ap.add_argument("--gene-list", action="append", default=[],
                    help="LABEL=PATH for plain gene-list .txt. Can repeat.")
    ap.add_argument("--padj-thr", type=float, default=0.05,
                    help="padj threshold for sig sets from --deg-csv (default 0.05).")
    ap.add_argument("--lfc-thr", type=float, default=0.5,
                    help="abs(log2FC) threshold for sig sets from --deg-csv (default 0.5).")
    ap.add_argument("--basemean-thr", type=float, default=0.0,
                    help="baseMean threshold for sig sets from --deg-csv (default 0).")
    ap.add_argument("--target-set", required=True,
                    help="Comma-separated labels for the 'target' subset, e.g. 'JBX97,JBX99'. "
                         "Numerator = (intersect of these) - (union of OTHER labels).")
    ap.add_argument("--gene-id-col", default=None,
                    help="If --deg-csv has gene IDs in a column (not the index), specify it.")
    args = ap.parse_args()

    sets: dict[str, set[str]] = {}
    for arg in args.deg_csv:
        label, path = parse_kv(arg)
        s = gene_set_from_csv(path, args.padj_thr, args.lfc_thr, args.basemean_thr, args.gene_id_col)
        sets[label] = s
        print(f"# SET {label} (from CSV {path}): n={len(s)}")
    for arg in args.gene_list:
        label, path = parse_kv(arg)
        s = gene_set_from_txt(path)
        sets[label] = s
        print(f"# SET {label} (from text {path}): n={len(s)}")

    if not sets:
        sys.exit("ERROR: no input sets — pass --deg-csv or --gene-list at least once.")

    target = [t.strip() for t in args.target_set.split(",") if t.strip()]
    missing = [t for t in target if t not in sets]
    if missing:
        sys.exit(f"ERROR: --target-set labels not found: {missing}. Have: {list(sets.keys())}")

    others = [k for k in sets if k not in target]
    print(f"\n# target labels: {target}")
    print(f"# other labels:  {others}")

    # Numerator: (intersect of target sets) - (union of others)
    target_intersect = set.intersection(*[sets[t] for t in target]) if target else set()
    target_union = set.union(*[sets[t] for t in target]) if target else set()
    others_union = set.union(*[sets[k] for k in others]) if others else set()
    all_union = set.union(*sets.values())

    numerator = target_intersect - others_union
    print(f"\n# NUMERATOR target_intersect_minus_others = {len(numerator)}")
    print(f"# NUMERATOR target_intersect = {len(target_intersect)}")
    print(f"# NUMERATOR target_union = {len(target_union)}")
    print(f"# DENOMINATOR all_union = {len(all_union)}")
    print(f"# DENOMINATOR target_union = {len(target_union)}")

    print("\n# === Common percentage interpretations ===")
    if len(numerator) > 0 or True:
        n = len(numerator)
        for label, denom_label, denom in [
            (f"|target∩ - others| / |{target[0]}|", target[0], len(sets[target[0]])),
            (f"|target∩ - others| / |target∩|", "target_intersect", len(target_intersect)),
            (f"|target∩ - others| / |target∪|", "target_union", len(target_union)),
            (f"|target∩ - others| / |all∪|", "all_union", len(all_union)),
        ]:
            if denom > 0:
                print(f"# PCT {label}  ({n}/{denom}) = {100*n/denom:.4f}%")
            else:
                print(f"# PCT {label}  ({n}/0) = NA")

    # Per-pair overlaps for full visibility
    print("\n# === Pairwise overlaps (every pair) ===")
    labels = list(sets.keys())
    for i in range(len(labels)):
        for j in range(i+1, len(labels)):
            A, B = sets[labels[i]], sets[labels[j]]
            print(f"# OVERLAP {labels[i]} vs {labels[j]}: "
                  f"|A|={len(A)} |B|={len(B)} |A∩B|={len(A & B)} "
                  f"|A∪B|={len(A | B)} |A-B|={len(A - B)} |B-A|={len(B - A)}")

    # Per-set unique-only and pairwise-only and triple-only counts (when 3 sets)
    if len(sets) == 3:
        print("\n# === Three-set Venn region sizes ===")
        a_lbl, b_lbl, c_lbl = labels
        A, B, C = sets[a_lbl], sets[b_lbl], sets[c_lbl]
        print(f"# only {a_lbl}: {len(A - B - C)}")
        print(f"# only {b_lbl}: {len(B - A - C)}")
        print(f"# only {c_lbl}: {len(C - A - B)}")
        print(f"# {a_lbl}∩{b_lbl} only: {len((A & B) - C)}")
        print(f"# {a_lbl}∩{c_lbl} only: {len((A & C) - B)}")
        print(f"# {b_lbl}∩{c_lbl} only: {len((B & C) - A)}")
        print(f"# all 3: {len(A & B & C)}")
        print(f"# union: {len(A | B | C)}")

    print("\n# DONE")


if __name__ == "__main__":
    main()
