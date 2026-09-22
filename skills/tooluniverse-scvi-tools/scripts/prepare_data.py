#!/usr/bin/env python3
"""
Prepare an .h5ad file for scvi-tools: QC-filter, select HVGs, and stash raw
integer counts in a 'counts' layer before any normalization touches .X.

This intentionally duplicates a *minimal* QC pass rather than depending on
tooluniverse-single-cell -- if that skill's scrna_qc.py has already been run,
point --input at its output and pass --skip-qc.

Usage:
    python prepare_data.py --install-plan
    python prepare_data.py raw.h5ad prepared.h5ad --batch-key batch
    python prepare_data.py qc_done.h5ad prepared.h5ad --skip-qc --n-hvgs 2000
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _scvi_common import preflight, print_install_plan  # noqa: E402


def main():
    p = argparse.ArgumentParser(description="Prepare AnnData for scvi-tools")
    p.add_argument("input", nargs="?", help="input .h5ad")
    p.add_argument("output", nargs="?", help="output prepared .h5ad")
    p.add_argument("--install-plan", action="store_true")
    p.add_argument("--batch-key", default=None, help="obs column identifying batches")
    p.add_argument("--n-hvgs", type=int, default=2000)
    p.add_argument("--min-genes", type=int, default=200)
    p.add_argument("--min-cells", type=int, default=3)
    p.add_argument(
        "--skip-qc",
        action="store_true",
        help="skip min-genes/min-cells filtering (use if already QC'd, e.g. by "
        "tooluniverse-single-cell/scripts/scrna_qc.py)",
    )
    args = p.parse_args()

    ok, missing = preflight(require=("anndata", "scanpy", "numpy"))
    if args.install_plan or not args.input or not args.output:
        print_install_plan(missing)
        return 0
    if not ok:
        print_install_plan(missing)
        print("Cannot prepare data without scanpy/anndata. Exiting cleanly (0).")
        return 0

    import anndata as ad
    import scanpy as sc

    adata = ad.read_h5ad(args.input)
    print(f"Loaded: {adata.n_obs} cells x {adata.n_vars} genes")

    if not args.skip_qc:
        sc.pp.filter_cells(adata, min_genes=args.min_genes)
        sc.pp.filter_genes(adata, min_cells=args.min_cells)
        print(f"After basic QC filter: {adata.n_obs} cells x {adata.n_vars} genes")

    # Stash raw integer counts BEFORE any normalization touches .X.
    adata.layers["counts"] = adata.X.copy()

    if args.batch_key and args.batch_key not in adata.obs:
        print(f"WARNING: --batch-key '{args.batch_key}' not found in obs; "
              f"continuing without batch info (scVI will train unbatched).")
        args.batch_key = None

    sc.pp.normalize_total(adata, target_sum=1e4)
    sc.pp.log1p(adata)
    adata.raw = adata.copy()

    hvg_kwargs = dict(n_top_genes=args.n_hvgs, flavor="seurat_v3", layer="counts")
    if args.batch_key:
        hvg_kwargs["batch_key"] = args.batch_key
    sc.pp.highly_variable_genes(adata, **hvg_kwargs)
    n_hvg = int(adata.var["highly_variable"].sum())
    print(f"Selected {n_hvg} highly variable genes (requested {args.n_hvgs})")
    adata = adata[:, adata.var["highly_variable"]].copy()

    adata.write_h5ad(args.output)
    print(f"Wrote prepared AnnData: {args.output}")
    print(
        "Next: python train_model.py "
        f"{args.output} results/ --model scvi"
        + (f" --batch-key {args.batch_key}" if args.batch_key else "")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
