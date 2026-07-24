#!/usr/bin/env python3
"""Query DepMap CRISPR (Chronos) gene-dependency scores per cancer cell line.

ToolUniverse's `DepMap_get_gene_dependencies` returns gene *metadata*, not the
per-cell-line Chronos scores. Those live in a bulk file (CRISPRGeneEffect.csv),
not a REST API. This helper downloads the current DepMap Public release once
(cached) via the public download index and answers the dependency questions a
functional-genomics / cell-line workflow needs.

Chronos gene-effect score interpretation:
- ~0   = no effect (knockout doesn't change fitness)
- < -0.5 ≈ DEPENDENCY (cell line needs this gene)
- ~ -1  = as essential as the median common-essential gene
LOWER (more negative) = MORE dependent.

Usage:
    python depmap_gene_dependency.py gene KRAS                 # cell lines most dependent on KRAS
    python depmap_gene_dependency.py gene KRAS --lineage Lung  # restrict to a lineage
    python depmap_gene_dependency.py cell-line A375 --top 25   # genes A375 most depends on

First call downloads CRISPRGeneEffect.csv (large, ~0.5 GB) + Model.csv and caches
them under the OS temp dir; later calls are fast. Requires pandas.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import tempfile
import urllib.request

DEPMAP_INDEX = "https://depmap.org/portal/api/download/files"
CACHE_DIR = os.path.join(tempfile.gettempdir(), "depmap_cache")


def _latest_url(filename: str) -> str:
    """Resolve the freshest signed download URL for a DepMap file (URLs expire)."""
    with urllib.request.urlopen(DEPMAP_INDEX, timeout=60) as fh:
        rows = list(csv.DictReader(fh.read().decode("utf-8", "ignore").splitlines()))

    def ver(r):
        m = re.search(r"(\d\d)Q(\d)", r["release"])
        return (int(m.group(1)), int(m.group(2))) if m else (-1, -1)

    cand = [r for r in rows if r["filename"] == filename and "Public" in r["release"]]
    if not cand:
        raise RuntimeError(f"{filename} not found in DepMap download index")
    cand.sort(key=ver)
    return cand[-1]["url"]


def _cached(filename: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, filename)
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        sys.stderr.write(f"Downloading {filename} (one-time; CRISPRGeneEffect is large)...\n")
        urllib.request.urlretrieve(_latest_url(filename), path)
    return path


def _models():
    import pandas as pd

    m = pd.read_csv(_cached("Model.csv"))
    keep = [c for c in ["ModelID", "CellLineName", "StrippedCellLineName",
                        "OncotreeLineage", "OncotreePrimaryDisease"] if c in m.columns]
    return m[keep]


def _find_gene_column(header, gene):
    """CRISPRGeneEffect columns are 'SYMBOL (ENTREZ)'. Match the symbol."""
    g = gene.strip().upper()
    for col in header:
        if col.split(" (")[0].strip().upper() == g:
            return col
    return None


def by_gene(gene, lineage=None, top=25):
    import pandas as pd

    path = _cached("CRISPRGeneEffect.csv")
    header = pd.read_csv(path, nrows=0).columns.tolist()
    idx_col = header[0]
    col = _find_gene_column(header[1:], gene)
    if col is None:
        return None
    df = pd.read_csv(path, usecols=[idx_col, col]).rename(
        columns={idx_col: "ModelID", col: "chronos"}
    )
    df = df.merge(_models(), on="ModelID", how="left").dropna(subset=["chronos"])
    if lineage:
        df = df[df["OncotreeLineage"].astype(str).str.contains(lineage, case=False, na=False)]
    cols = [c for c in ["StrippedCellLineName", "OncotreeLineage", "OncotreePrimaryDisease", "chronos"] if c in df.columns]
    return df.sort_values("chronos")[cols].head(top)


def by_cell_line(name, top=25):
    import pandas as pd

    models = _models()
    hit = models[
        models["StrippedCellLineName"].astype(str).str.upper() == name.strip().upper()
    ]
    if hit.empty:
        hit = models[models["CellLineName"].astype(str).str.upper() == name.strip().upper()]
    if hit.empty:
        return None
    model_id = hit.iloc[0]["ModelID"]
    # Read just this cell line's row (the file is wide; load and select the row).
    df = pd.read_csv(_cached("CRISPRGeneEffect.csv"), index_col=0)
    if model_id not in df.index:
        return None
    row = df.loc[model_id].sort_values()
    out = row.head(top).reset_index()
    out.columns = ["gene", "chronos"]
    # strip the trailing " (ENTREZ)"; pat is a literal, not a regex
    out["gene"] = out["gene"].str.replace(r"\s*\(\d+\)$", "", regex=True)
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=["gene", "cell-line"])
    p.add_argument("value")
    p.add_argument("--lineage", default=None, help="Restrict gene mode to a lineage (e.g. Lung)")
    p.add_argument("--top", type=int, default=25)
    args = p.parse_args(argv)

    out = by_gene(args.value, args.lineage, args.top) if args.mode == "gene" else by_cell_line(args.value, args.top)
    if out is None or out.empty:
        sys.stderr.write(
            f"No DepMap data for {args.mode}='{args.value}'. Use the gene SYMBOL "
            "(e.g. KRAS) or stripped cell-line name (e.g. A375).\n"
        )
        return 1
    import pandas as pd

    with pd.option_context("display.max_rows", None, "display.width", 200):
        print(out.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
