# scVI / scANVI Integration Workflow

## When to reach for this instead of Harmony

`tooluniverse-single-cell` covers Harmony-based batch correction (linear,
fast, works on the PCA embedding). Reach for scVI/scANVI instead when:

- Batch effects are strong and nonlinear (different sequencing platforms /
  chemistries, e.g. 10x v2 vs v3, or cross-species integration).
- You want denoised expression estimates (imputation), not just a corrected
  embedding.
- You have partial cell-type labels and want semi-supervised integration
  that respects them (scANVI) rather than fully unsupervised (scVI).
- You need to map new query data onto an existing reference later
  (scANVI + `load_query_data`, i.e. scArches-style reference mapping).

## End-to-end (scVI)

```bash
python validate_adata.py raw.h5ad --batch-key batch --suggest
python prepare_data.py raw.h5ad prepared.h5ad --batch-key batch --n-hvgs 2000
python train_model.py prepared.h5ad results/ --model scvi --batch-key batch
```

`train_model.py` writes `results/scvi_model/` (the trained model) and
`results/adata_scvi_trained.h5ad` (input data + `obsm['X_scvi']` latent
space). From there, standard scanpy clustering on the latent space:

```python
import scanpy as sc, anndata as ad
adata = ad.read_h5ad("results/adata_scvi_trained.h5ad")
sc.pp.neighbors(adata, use_rep="X_scvi")
sc.tl.leiden(adata, resolution=0.5)
sc.tl.umap(adata)
```

## End-to-end (scANVI, with labels)

```bash
python train_model.py prepared.h5ad results/ --model scanvi \
    --batch-key batch --label-key cell_type --unlabeled-category Unknown
```

Cells with `cell_type == "Unknown"` (or your `--unlabeled-category`) are
treated as unlabeled and get predicted labels via `model.predict()` after
training -- useful for annotating a partially-labeled atlas in one pass,
distinct from `transfer_labels.py` which maps an entirely separate query
dataset onto an already-trained reference.

## Interpreting training

- **ELBO should decrease and plateau.** If it is flat from epoch 1 or
  diverges (NaN/inf), see `troubleshooting.md`.
- **`n_latent` default is 10.** Increase (20-30) for very heterogeneous
  atlases with many expected cell types; decrease (5-8) for a narrow,
  homogeneous population -- too many latent dimensions on a small dataset
  overfits and produces speckled, non-biological clusters.
- **A trained model is not automatically "correct."** Always visualize the
  resulting UMAP colored by batch (should mix) and by a few canonical marker
  genes (should still separate cell types) before trusting the integration.

## Differential expression after integration

Use the model's own posterior DE (`differential_expression.py`), not
scanpy's `rank_genes_groups`, on the trained model + its adata -- it
accounts for the model's estimated uncertainty rather than treating
normalized counts as ground truth. See `../scripts/differential_expression.py`.
