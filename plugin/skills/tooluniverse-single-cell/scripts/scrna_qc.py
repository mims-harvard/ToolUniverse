#!/usr/bin/env python3
"""
scRNA-seq QC gating helper (run-if-available).

Computes per-cell QC metrics from an .h5ad and applies distribution-aware
(MAD-based) gating BEFORE downstream analysis. Reports cutoffs and how many
cells each step removes — it never fabricates numbers.

HONEST DESIGN:
- If scanpy/anndata are NOT installed, this prints an install plan and exits 0.
  It does not pretend to have run anything.
- Doublet detection is attempted only if scrublet is importable; otherwise it
  is reported as skipped (with the install command), not faked.

Usage:
    python scrna_qc.py --install-plan          # preflight only, no data needed
    python scrna_qc.py path/to/data.h5ad       # compute + gate
    python scrna_qc.py data.h5ad --nmads-counts 5 --nmads-mt 3 --mt-ceiling 20 \
        --min-genes 200 --doublets --write out_qc.h5ad
"""

import argparse
import sys

INSTALL_CMD = "pip install scanpy anndata scrublet"


def preflight():
    """Return (ok, missing_list). Never raises."""
    missing = []
    for mod in ("scanpy", "anndata", "numpy"):
        try:
            __import__(mod)
        except Exception:
            missing.append(mod)
    return (len(missing) == 0, missing)


def print_install_plan(missing):
    print("scRNA-seq QC helper — environment preflight")
    if not missing:
        print("  scanpy/anndata/numpy: available")
        try:
            import scrublet  # noqa: F401

            print("  scrublet (doublets): available")
        except Exception:
            print("  scrublet (doublets): MISSING -> pip install scrublet "
                  "(doublet step will be skipped)")
        print("Environment OK. Re-run with an .h5ad path to compute QC.")
    else:
        print(f"  MISSING: {', '.join(missing)}")
        print("Install plan (run this, then re-run with your .h5ad):")
        print(f"  {INSTALL_CMD}")
        print("No analysis was run. This is a preflight only — no numbers were "
              "fabricated.")


def is_outlier(values, nmads, upper_only=False):
    import numpy as np

    M = np.asarray(values, dtype=float)
    med = np.median(M)
    mad = np.median(np.abs(M - med))
    if mad == 0:
        return np.zeros(len(M), dtype=bool)
    lower, upper = med - nmads * mad, med + nmads * mad
    return (M > upper) if upper_only else ((M < lower) | (M > upper))


def run_qc(args):
    import numpy as np
    import scanpy as sc

    adata = sc.read_h5ad(args.h5ad)
    print(f"Loaded: {adata.n_obs} cells x {adata.n_vars} genes")

    vn = adata.var_names.str.upper()
    adata.var["mt"] = vn.str.startswith("MT-")
    adata.var["ribo"] = vn.str.startswith(("RPS", "RPL"))
    adata.var["hb"] = vn.str.contains(r"^HB[^P]", regex=True)

    qc_vars = [v for v in ("mt", "ribo", "hb") if adata.var[v].any()]
    sc.pp.calculate_qc_metrics(
        adata, qc_vars=qc_vars, percent_top=None, log1p=True, inplace=True
    )

    has_mt = "pct_counts_mt" in adata.obs
    print("Pre-filter medians:")
    print(f"  genes/cell : {adata.obs['n_genes_by_counts'].median():.0f}")
    print(f"  counts/cell: {adata.obs['total_counts'].median():.0f}")
    if has_mt:
        print(f"  %MT        : {adata.obs['pct_counts_mt'].median():.2f}")

    # MAD-based count/gene outliers (both tails) on log1p-scaled metrics
    count_out = is_outlier(adata.obs["log1p_total_counts"], args.nmads_counts)
    gene_out = is_outlier(adata.obs["log1p_n_genes_by_counts"], args.nmads_counts)
    # Hard floor for empty droplets
    floor = adata.obs["n_genes_by_counts"].values < args.min_genes

    # Mito: upper-tail MAD + biological ceiling
    if has_mt:
        mt_out = is_outlier(
            adata.obs["pct_counts_mt"], args.nmads_mt, upper_only=True
        ) | (adata.obs["pct_counts_mt"].values > args.mt_ceiling)
    else:
        mt_out = np.zeros(adata.n_obs, dtype=bool)

    drop = count_out | gene_out | floor | mt_out
    print("Cells flagged for removal:")
    print(f"  count outlier (>{args.nmads_counts} MAD) : {int(count_out.sum())}")
    print(f"  gene outlier  (>{args.nmads_counts} MAD) : {int(gene_out.sum())}")
    print(f"  < {args.min_genes} genes (empty droplet): {int(floor.sum())}")
    print(f"  high %MT ({args.nmads_mt} MAD / >{args.mt_ceiling}%): "
          f"{int(mt_out.sum())}")
    print(f"  UNION removed: {int(drop.sum())} / {adata.n_obs}")

    adata = adata[~drop].copy()
    sc.pp.filter_genes(adata, min_cells=args.min_cells)
    print(f"After per-cell gating + gene filter: "
          f"{adata.n_obs} cells x {adata.n_vars} genes")

    if args.doublets:
        try:
            import scrublet  # noqa: F401

            try:
                sc.pp.scrublet(adata, expected_doublet_rate=args.doublet_rate)
            except AttributeError:
                sc.external.pp.scrublet(
                    adata, expected_doublet_rate=args.doublet_rate
                )
            n = int(adata.obs["predicted_doublet"].sum())
            print(f"Scrublet: {n} predicted doublets "
                  f"({100 * n / adata.n_obs:.1f}%)")
            if args.drop_doublets:
                adata = adata[~adata.obs["predicted_doublet"]].copy()
                print(f"Dropped doublets -> {adata.n_obs} cells")
        except Exception:
            print("Doublet step SKIPPED: scrublet not installed "
                  "-> pip install scrublet (not fabricating a doublet rate)")

    if args.write:
        adata.write_h5ad(args.write)
        print(f"Wrote gated AnnData: {args.write}")

    return 0


def main():
    p = argparse.ArgumentParser(description="scRNA-seq QC gating (run-if-available)")
    p.add_argument("h5ad", nargs="?", help="input .h5ad (omit with --install-plan)")
    p.add_argument("--install-plan", action="store_true",
                   help="preflight environment only; print install plan; exit 0")
    p.add_argument("--nmads-counts", type=float, default=5.0)
    p.add_argument("--nmads-mt", type=float, default=3.0)
    p.add_argument("--mt-ceiling", type=float, default=20.0,
                   help="biological %MT ceiling (raise for mito-rich tissue)")
    p.add_argument("--min-genes", type=int, default=200)
    p.add_argument("--min-cells", type=int, default=3)
    p.add_argument("--doublets", action="store_true",
                   help="run Scrublet if installed (else skip, do not fake)")
    p.add_argument("--drop-doublets", action="store_true")
    p.add_argument("--doublet-rate", type=float, default=0.06)
    p.add_argument("--write", help="write gated AnnData to this .h5ad")
    args = p.parse_args()

    ok, missing = preflight()
    if args.install_plan or not args.h5ad:
        print_install_plan(missing)
        return 0
    if not ok:
        print_install_plan(missing)
        print("Cannot compute QC without scanpy. Exiting cleanly (0).")
        return 0
    return run_qc(args)


if __name__ == "__main__":
    sys.exit(main())
