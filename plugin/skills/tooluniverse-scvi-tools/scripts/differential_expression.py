#!/usr/bin/env python3
"""
Differential expression from a trained scVI or scANVI model, grouped by an
obs column (e.g. leiden cluster or cell type).

Uses the model's own posterior-based DE (change-mode Bayesian DE), which is
NOT the same as scanpy's rank_genes_groups -- it accounts for the model's
uncertainty rather than treating normalized counts as exact.

Usage:
    python differential_expression.py --install-plan
    python differential_expression.py results/scvi_model results/adata_scvi_trained.h5ad \
        de.csv --groupby leiden
    python differential_expression.py results/scvi_model results/adata_scvi_trained.h5ad \
        de.csv --groupby condition --group1 treated --group2 control
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _scvi_common import preflight, print_install_plan  # noqa: E402


def main():
    p = argparse.ArgumentParser(description="scvi-tools posterior differential expression")
    p.add_argument("model_dir", nargs="?", help="directory saved by train_model.py")
    p.add_argument("h5ad", nargs="?", help="the trained adata (must match the model)")
    p.add_argument("output_csv", nargs="?")
    p.add_argument("--install-plan", action="store_true")
    p.add_argument("--model-class", choices=["scvi", "scanvi"], default="scvi")
    p.add_argument("--groupby", required=False, help="obs column defining groups")
    p.add_argument("--group1", default=None, help="one-vs-rest if omitted")
    p.add_argument("--group2", default=None, help="compare against this group instead of rest")
    p.add_argument("--delta", type=float, default=0.25, help="log-fold-change threshold for change mode")
    args = p.parse_args()

    ok, missing = preflight(require=("scvi", "anndata", "pandas"))
    if args.install_plan or not (args.model_dir and args.h5ad and args.output_csv):
        print_install_plan(missing)
        return 0
    if not ok:
        print_install_plan(missing)
        print("Cannot run DE without scvi-tools. Exiting cleanly (0).")
        return 0
    if not args.groupby:
        print("ERROR: --groupby is required (an obs column, e.g. 'leiden' or 'condition').")
        return 1

    import anndata as ad
    import scvi

    adata = ad.read_h5ad(args.h5ad)
    if args.groupby not in adata.obs:
        print(f"ERROR: --groupby '{args.groupby}' not found in adata.obs. "
              f"Available columns: {list(adata.obs.columns)}")
        return 1

    cls = scvi.model.SCANVI if args.model_class == "scanvi" else scvi.model.SCVI
    model = cls.load(args.model_dir, adata=adata)

    kwargs = dict(groupby=args.groupby, delta=args.delta)
    if args.group1:
        kwargs["group1"] = [args.group1]
    if args.group2:
        kwargs["group2"] = args.group2

    print(f"Running DE (model={args.model_class}, groupby={args.groupby}, "
          f"group1={args.group1 or 'ALL'}, group2={args.group2 or 'rest'})")
    de_df = model.differential_expression(**kwargs)
    de_df.to_csv(args.output_csv)
    n_sig = int((de_df["is_de_fdr_0.05"]).sum()) if "is_de_fdr_0.05" in de_df.columns else None
    print(f"Wrote {len(de_df)} genes to {args.output_csv}"
          + (f" ({n_sig} significant at FDR 0.05)" if n_sig is not None else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
