#!/usr/bin/env python3
"""
scANVI-based label transfer / reference mapping: given a trained scANVI
reference model and a new (query) .h5ad of unlabeled cells, map the query
into the reference latent space and predict labels.

Usage:
    python transfer_labels.py --install-plan
    python transfer_labels.py results/scanvi_model reference.h5ad query.h5ad results/
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _scvi_common import preflight, print_install_plan, report_device, require_raw_counts  # noqa: E402


def main():
    p = argparse.ArgumentParser(description="scANVI label transfer / reference mapping")
    p.add_argument("ref_model_dir", nargs="?", help="directory saved by train_model.py --model scanvi")
    p.add_argument("ref_h5ad", nargs="?", help="the reference adata used to train ref_model_dir")
    p.add_argument("query_h5ad", nargs="?", help="new, unlabeled .h5ad to map onto the reference")
    p.add_argument("outdir", nargs="?")
    p.add_argument("--install-plan", action="store_true")
    p.add_argument("--label-key", default=None, help="obs column name for predicted labels in the output (default: same as reference)")
    p.add_argument("--max-epochs", type=int, default=None, help="query fine-tuning epochs; small value for a quick check")
    args = p.parse_args()

    ok, missing = preflight(require=("scvi", "anndata", "numpy"))
    required_paths = (args.ref_model_dir, args.ref_h5ad, args.query_h5ad, args.outdir)
    if args.install_plan or not all(required_paths):
        print_install_plan(missing)
        return 0
    if not ok:
        print_install_plan(missing)
        print("Cannot transfer labels without scvi-tools. Exiting cleanly (0).")
        return 0

    import anndata as ad
    import scvi

    ref_adata = ad.read_h5ad(args.ref_h5ad)
    query_adata = ad.read_h5ad(args.query_h5ad)
    print(f"Reference: {ref_adata.n_obs} cells x {ref_adata.n_vars} genes")
    print(f"Query:     {query_adata.n_obs} cells x {query_adata.n_vars} genes")

    try:
        require_raw_counts(query_adata, layer="counts")
    except ValueError as e:
        print(f"ERROR: {e}")
        return 1

    shared_genes = ref_adata.var_names.intersection(query_adata.var_names)
    print(f"Shared genes between reference and query: {len(shared_genes)} / "
          f"{ref_adata.n_vars} reference genes")
    if len(shared_genes) < 0.5 * ref_adata.n_vars:
        print(
            "WARNING: fewer than half of the reference's genes are present in "
            "the query. scArches-style mapping expects the same gene panel -- "
            "results may be unreliable. Consider re-running prepare_data.py on "
            "both datasets with a shared HVG list."
        )

    report_device()

    ref_model = scvi.model.SCANVI.load(args.ref_model_dir, adata=ref_adata)

    print("Loading query data onto the reference model (scArches-style surgery)...")
    query_model = scvi.model.SCANVI.load_query_data(query_adata, args.ref_model_dir)
    query_model.train(max_epochs=args.max_epochs, plan_kwargs={"weight_decay": 0.0})

    predicted = query_model.predict()
    latent = query_model.get_latent_representation()

    label_col = args.label_key or "predicted_label"
    query_adata.obs[label_col] = predicted
    query_adata.obsm["X_scanvi_query"] = latent

    os.makedirs(args.outdir, exist_ok=True)
    out_h5ad = os.path.join(args.outdir, "query_mapped.h5ad")
    query_adata.write_h5ad(out_h5ad)

    from collections import Counter

    counts = Counter(predicted)
    print(f"Predicted label distribution ({label_col}):")
    for label, n in counts.most_common():
        print(f"  {label}: {n} ({100 * n / len(predicted):.1f}%)")
    print(f"Wrote mapped query with predictions -> {out_h5ad}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
