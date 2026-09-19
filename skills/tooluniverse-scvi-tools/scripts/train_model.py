#!/usr/bin/env python3
"""
Train an scvi-tools model on a prepared .h5ad file.

Supports --model scvi|scanvi|totalvi|peakvi|multivi|velovi. For DestVI
(spatial deconvolution), see references/multimodal_workflows.md -- it needs
two AnnData objects (single-cell reference + spatial query) and is run as a
two-stage fit, not a single train_model.py call.

Usage:
    python train_model.py --install-plan
    python train_model.py prepared.h5ad results/ --model scvi --batch-key batch
    python train_model.py prepared.h5ad results/ --model scanvi --batch-key batch \
        --label-key cell_type
    python train_model.py prepared.h5ad results/ --model totalvi --protein-obsm protein_counts
    python train_model.py prepared.h5ad results/ --model scvi --max-epochs 2  # smoke test
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _scvi_common import preflight, print_install_plan, report_device, require_raw_counts  # noqa: E402


MODEL_REQUIRES = {
    "scvi": (),
    "scanvi": ("label_key",),
    "totalvi": ("protein_obsm",),
    "peakvi": (),
    "multivi": (),
    "velovi": (),
}


def train_scvi(adata, args):
    import scvi

    scvi.model.SCVI.setup_anndata(adata, layer="counts", batch_key=args.batch_key)
    model = scvi.model.SCVI(adata, n_latent=args.n_latent)
    model.train(max_epochs=args.max_epochs)
    return model


def train_scanvi(adata, args):
    import scvi

    scvi.model.SCANVI.setup_anndata(
        adata,
        layer="counts",
        batch_key=args.batch_key,
        labels_key=args.label_key,
        unlabeled_category=args.unlabeled_category,
    )
    model = scvi.model.SCANVI(adata, n_latent=args.n_latent)
    model.train(max_epochs=args.max_epochs)
    return model


def train_totalvi(adata, args):
    import scvi

    scvi.model.TOTALVI.setup_anndata(
        adata,
        layer="counts",
        batch_key=args.batch_key,
        protein_expression_obsm_key=args.protein_obsm,
    )
    model = scvi.model.TOTALVI(adata, n_latent=args.n_latent)
    model.train(max_epochs=args.max_epochs)
    return model


def train_peakvi(adata, args):
    import scvi

    scvi.model.PEAKVI.setup_anndata(adata, layer="counts", batch_key=args.batch_key)
    model = scvi.model.PEAKVI(adata, n_latent=args.n_latent)
    model.train(max_epochs=args.max_epochs)
    return model


def train_multivi(adata, args):
    import scvi

    n_genes = int((adata.var["modality"] == "Gene Expression").sum()) if "modality" in adata.var else adata.n_vars
    n_regions = adata.n_vars - n_genes
    scvi.model.MULTIVI.setup_anndata(adata, layer="counts", batch_key=args.batch_key)
    model = scvi.model.MULTIVI(adata, n_genes=n_genes, n_regions=n_regions)
    model.train(max_epochs=args.max_epochs)
    return model


def train_velovi(adata, args):
    from scvi.external import VELOVI

    VELOVI.setup_anndata(adata, spliced_layer="spliced", unspliced_layer="unspliced")
    model = VELOVI(adata)
    model.train(max_epochs=args.max_epochs)
    return model


TRAINERS = {
    "scvi": train_scvi,
    "scanvi": train_scanvi,
    "totalvi": train_totalvi,
    "peakvi": train_peakvi,
    "multivi": train_multivi,
    "velovi": train_velovi,
}


def main():
    p = argparse.ArgumentParser(description="Train an scvi-tools model")
    p.add_argument("input", nargs="?", help="prepared .h5ad (from prepare_data.py)")
    p.add_argument("outdir", nargs="?", help="output directory for model + results")
    p.add_argument("--install-plan", action="store_true")
    p.add_argument("--model", choices=sorted(TRAINERS), default="scvi")
    p.add_argument("--batch-key", default=None)
    p.add_argument("--label-key", default=None, help="required for --model scanvi")
    p.add_argument("--unlabeled-category", default="Unknown")
    p.add_argument("--protein-obsm", default=None, help="required for --model totalvi")
    p.add_argument("--n-latent", type=int, default=10)
    p.add_argument("--max-epochs", type=int, default=None, help="default: scvi-tools' own heuristic; use a small value (2-5) for a quick smoke test")
    args = p.parse_args()

    ok, missing = preflight(require=("scvi", "anndata", "numpy"))
    if args.install_plan or not args.input or not args.outdir:
        print_install_plan(missing)
        return 0
    if not ok:
        print_install_plan(missing)
        print("Cannot train without scvi-tools. Exiting cleanly (0).")
        return 0

    for req in MODEL_REQUIRES[args.model]:
        if getattr(args, req) is None:
            print(f"ERROR: --model {args.model} requires --{req.replace('_', '-')}.")
            print("No training was started -- refusing to guess a value for a "
                  "required argument.")
            return 1

    import anndata as ad

    adata = ad.read_h5ad(args.input)
    print(f"Loaded: {adata.n_obs} cells x {adata.n_vars} genes")

    if args.model != "velovi":
        try:
            require_raw_counts(adata, layer="counts")
        except ValueError as e:
            print(f"ERROR: {e}")
            return 1

    report_device()

    model = TRAINERS[args.model](adata, args)

    os.makedirs(args.outdir, exist_ok=True)
    model_dir = os.path.join(args.outdir, f"{args.model}_model")
    model.save(model_dir, overwrite=True)
    print(f"Saved trained model: {model_dir}")

    if hasattr(model, "get_latent_representation"):
        latent = model.get_latent_representation()
        adata.obsm[f"X_{args.model}"] = latent
        out_h5ad = os.path.join(args.outdir, f"adata_{args.model}_trained.h5ad")
        adata.write_h5ad(out_h5ad)
        print(f"Wrote latent representation into obsm['X_{args.model}'] -> {out_h5ad}")
        print(
            "Next: python cluster_embed.py (scanpy neighbors/leiden/umap on "
            f"obsm['X_{args.model}']), or differential_expression.py for DE."
        )
    else:
        print(
            f"{args.model} does not expose a standard latent representation via "
            "get_latent_representation(); see references/ for its own output API."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
