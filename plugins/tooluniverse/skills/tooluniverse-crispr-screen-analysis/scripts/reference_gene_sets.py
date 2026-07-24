#!/usr/bin/env python3
"""Reference core-essential / non-essential gene sets for CRISPR-screen scoring.

BAGEL Bayes-Factor scoring and the screen-QC check ("are known essential genes
recovered?") both require the published reference gene sets. The small hardcoded
stubs in the inline examples are not sufficient. This module loads the bundled
full lists:

- CEGv2 (Hart et al. 2017): ~684 core-essential genes
- NEGv1 (Hart & Moffat 2016): ~928 non-essential (reference-negative) genes

Both are the standard sets distributed with BAGEL (github.com/hart-lab/bagel).

Usage:
    from reference_gene_sets import core_essential, nonessential
    ess = core_essential()      # set[str] of gene symbols
    neg = nonessential()
"""

from __future__ import annotations

import os
from functools import lru_cache

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load(filename: str) -> set:
    path = os.path.join(_HERE, filename)
    with open(path) as fh:
        return {line.strip() for line in fh if line.strip()}


@lru_cache(maxsize=None)
def core_essential() -> set:
    """CEGv2 core-essential gene symbols (Hart et al.)."""
    return _load("CEGv2_core_essential.txt")


@lru_cache(maxsize=None)
def nonessential() -> set:
    """NEGv1 non-essential reference gene symbols (Hart & Moffat)."""
    return _load("NEGv1_nonessential.txt")


def recovery_rate(hit_genes) -> float:
    """Fraction of CEGv2 core-essential genes recovered among `hit_genes`.

    A good genome-wide CRISPR knockout screen recovers a high fraction (>~0.8)
    of core-essential genes among its top depleted hits -- a standard QC metric.
    """
    ess = core_essential()
    hits = set(hit_genes) & ess
    return len(hits) / len(ess) if ess else 0.0


if __name__ == "__main__":
    print(f"core-essential (CEGv2): {len(core_essential())} genes")
    print(f"non-essential (NEGv1):  {len(nonessential())} genes")
    print("sample essential:", sorted(core_essential())[:5])
