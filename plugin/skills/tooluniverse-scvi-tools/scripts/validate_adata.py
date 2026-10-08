#!/usr/bin/env python3
"""
Check whether an .h5ad file is ready for scvi-tools training, and (with
--suggest) recommend which model fits the data.

Usage:
    python validate_adata.py --install-plan
    python validate_adata.py data.h5ad
    python validate_adata.py data.h5ad --batch-key batch --suggest
    python validate_adata.py data.h5ad --protein-layer protein --suggest
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _scvi_common import preflight, print_install_plan  # noqa: E402


def suggest_model(adata, args):
    reasons = []
    if args.protein_obsm and args.protein_obsm in adata.obsm:
        reasons.append(
            ("totalVI", f"'{args.protein_obsm}' obsm matrix present -> CITE-seq protein+RNA")
        )
    if args.atac_layer and (
        args.atac_layer in adata.layers or args.atac_layer in getattr(adata, "obsm", {})
    ):
        reasons.append(("PeakVI/MultiVI", f"ATAC data found under '{args.atac_layer}'"))
    if args.label_key and args.label_key in adata.obs:
        n_labeled = adata.obs[args.label_key].notna().sum()
        reasons.append(
            (
                "scANVI",
                f"'{args.label_key}' has {n_labeled}/{adata.n_obs} labeled cells "
                "-> semi-supervised integration / label transfer",
            )
        )
    if args.batch_key and args.batch_key in adata.obs:
        n_batches = adata.obs[args.batch_key].nunique()
        if not reasons:
            reasons.append(
                ("scVI", f"'{args.batch_key}' has {n_batches} batches, no labels/multi-modal data -> plain unsupervised integration")
            )
    if not reasons:
        reasons.append(
            ("scVI", "no batch/label/protein/ATAC signal detected -> default to scVI for a general latent representation")
        )
    print("\nModel suggestion:")
    for model, why in reasons:
        print(f"  - {model}: {why}")
    print(
        "See references/model_selection.md for the full decision tree "
        "(covers MultiVI, DestVI, veloVI too)."
    )


def main():
    p = argparse.ArgumentParser(description="Validate an AnnData file for scvi-tools")
    p.add_argument("h5ad", nargs="?")
    p.add_argument("--install-plan", action="store_true")
    p.add_argument("--layer", default="counts", help="layer holding raw counts (default: counts)")
    p.add_argument("--batch-key", default=None)
    p.add_argument("--label-key", default=None)
    p.add_argument("--protein-obsm", default=None, help="obsm key holding protein counts (CITE-seq)")
    p.add_argument("--atac-layer", default=None, help="layer/obsm key holding ATAC peak counts")
    p.add_argument("--suggest", action="store_true")
    args = p.parse_args()

    ok, missing = preflight(require=("anndata", "numpy"))
    if args.install_plan or not args.h5ad:
        print_install_plan(missing, extra_note="(scvi import is not required just to validate)")
        return 0
    if not ok:
        print_install_plan(missing)
        print("Cannot validate without anndata. Exiting cleanly (0).")
        return 0

    import numpy as np
    import anndata as ad

    adata = ad.read_h5ad(args.h5ad)
    print(f"Loaded: {adata.n_obs} cells x {adata.n_vars} genes")

    issues = []

    X = adata.layers[args.layer] if args.layer in adata.layers else adata.X
    src = f"layers['{args.layer}']" if args.layer in adata.layers else "X"
    sample = X[:200].toarray() if hasattr(X, "toarray") else np.asarray(X[:200])
    if sample.size:
        non_int_frac = float(np.mean(np.abs(sample - np.round(sample)) > 1e-6))
        neg_frac = float(np.mean(sample < 0))
        print(f"Counts check ({src}): {non_int_frac:.1%} non-integer, {neg_frac:.1%} negative")
        if non_int_frac > 0.01:
            issues.append(
                f"'{src}' does not look like raw integer counts. scvi-tools "
                f"needs raw counts -- run prepare_data.py or point --layer at "
                f"the correct layer."
            )
        if neg_frac > 0:
            issues.append(f"'{src}' has negative values -- not valid raw counts.")
    else:
        issues.append("AnnData has zero cells or genes.")

    if args.batch_key:
        if args.batch_key not in adata.obs:
            issues.append(f"--batch-key '{args.batch_key}' not found in adata.obs.")
        else:
            n = adata.obs[args.batch_key].nunique()
            print(f"Batch key '{args.batch_key}': {n} unique values")
            if n < 2:
                issues.append(
                    f"--batch-key '{args.batch_key}' has only {n} unique value(s) "
                    "-- nothing to integrate across."
                )

    if args.label_key and args.label_key not in adata.obs:
        issues.append(f"--label-key '{args.label_key}' not found in adata.obs.")

    if args.protein_obsm and args.protein_obsm not in adata.obsm:
        issues.append(f"--protein-obsm '{args.protein_obsm}' not found in adata.obsm.")

    if issues:
        print("\nISSUES FOUND (fix before training):")
        for i in issues:
            print(f"  - {i}")
    else:
        print("\nNo blocking issues found.")

    if args.suggest:
        suggest_model(adata, args)

    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
