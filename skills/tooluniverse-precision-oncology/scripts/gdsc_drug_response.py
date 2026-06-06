#!/usr/bin/env python3
"""Query GDSC cancer cell-line drug sensitivity (IC50 / AUC).

ToolUniverse has no DepMap/GDSC drug-response *tool* because the data is a bulk
download, not a REST API. This helper closes that gap: it downloads the public
GDSC fitted dose-response table once (cached locally) and answers the common
questions a precision-oncology workflow needs.

Data source (public, no auth): Genomics of Drug Sensitivity in Cancer (GDSC),
Sanger Institute / cancerrxgene.org. Columns include CELL_LINE_NAME, DRUG_NAME,
PUTATIVE_TARGET, PATHWAY_NAME, TCGA_DESC, LN_IC50, AUC, Z_SCORE.

Usage:
    python gdsc_drug_response.py drug "Trametinib"           # sensitivity across cell lines
    python gdsc_drug_response.py cell-line "A375"            # drugs tested on a cell line
    python gdsc_drug_response.py target "BRAF"               # drugs whose putative target is BRAF
    python gdsc_drug_response.py drug "Trametinib" --tcga SKCM --top 15

Notes:
- LN_IC50 is natural-log IC50 in micromolar; LOWER = more sensitive.
- Z_SCORE is per-drug across cell lines; negative = unusually sensitive.
- First call downloads ~21 MB (GDSC2) and caches under the OS temp dir.
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
import urllib.request

# GDSC2 is the current screen (more drugs, better QC). GDSC1 kept as a fallback.
GDSC_URLS = {
    "GDSC2": "https://cog.sanger.ac.uk/cancerrxgene/GDSC_release8.5/GDSC2_fitted_dose_response_27Oct23.xlsx",
    "GDSC1": "https://cog.sanger.ac.uk/cancerrxgene/GDSC_release8.5/GDSC1_fitted_dose_response_27Oct23.xlsx",
}
CACHE_DIR = os.path.join(tempfile.gettempdir(), "gdsc_cache")


def _cached_path(dataset: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"{dataset}_fitted_dose_response.xlsx")


def load_gdsc(dataset: str = "GDSC2"):
    """Return the fitted dose-response table as a pandas DataFrame (cached)."""
    import pandas as pd

    if dataset not in GDSC_URLS:
        raise ValueError(f"dataset must be one of {list(GDSC_URLS)}")
    path = _cached_path(dataset)
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        sys.stderr.write(f"Downloading {dataset} (~21 MB, one-time)...\n")
        urllib.request.urlretrieve(GDSC_URLS[dataset], path)
    return pd.read_excel(path)


_COLS = ["CELL_LINE_NAME", "TCGA_DESC", "DRUG_NAME", "PUTATIVE_TARGET", "LN_IC50", "AUC", "Z_SCORE"]


def _select(df, mask, tcga=None, top=20, sort="LN_IC50", ascending=True):
    sub = df[mask]
    if tcga:
        sub = sub[sub["TCGA_DESC"].astype(str).str.upper() == tcga.upper()]
    cols = [c for c in _COLS if c in sub.columns]
    return sub.sort_values(sort, ascending=ascending)[cols].head(top)


def by_drug(df, drug, tcga=None, top=20):
    """Most-sensitive cell lines for a drug (lowest LN_IC50 first)."""
    return _select(df, df["DRUG_NAME"].astype(str).str.lower() == drug.lower(), tcga, top)


def by_cell_line(df, cell_line, top=20):
    """Drugs the cell line is most sensitive to."""
    return _select(df, df["CELL_LINE_NAME"].astype(str).str.lower() == cell_line.lower(), None, top)


def by_target(df, target, tcga=None, top=20):
    """Drugs whose putative target contains the given gene symbol."""
    mask = df["PUTATIVE_TARGET"].astype(str).str.contains(rf"\b{target}\b", case=False, na=False)
    return _select(df, mask, tcga, top)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=["drug", "cell-line", "target"])
    p.add_argument("value")
    p.add_argument("--dataset", default="GDSC2", choices=list(GDSC_URLS))
    p.add_argument("--tcga", default=None, help="Filter by TCGA cancer type, e.g. SKCM, LUAD")
    p.add_argument("--top", type=int, default=20)
    args = p.parse_args(argv)

    df = load_gdsc(args.dataset)
    if args.mode == "drug":
        out = by_drug(df, args.value, args.tcga, args.top)
    elif args.mode == "cell-line":
        out = by_cell_line(df, args.value, args.top)
    else:
        out = by_target(df, args.value, args.tcga, args.top)

    if out.empty:
        sys.stderr.write(
            f"No GDSC rows for {args.mode}='{args.value}'"
            + (f" (tcga={args.tcga})" if args.tcga else "")
            + ". Check spelling against the GDSC naming (e.g. drug 'Trametinib', "
            "cell line 'A375', target gene 'BRAF').\n"
        )
        return 1
    import pandas as pd

    with pd.option_context("display.max_rows", None, "display.width", 200):
        print(out.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
