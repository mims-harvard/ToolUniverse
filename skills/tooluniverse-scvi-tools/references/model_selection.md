# scvi-tools Model Selection

Decision tree first, then a table with minimum data requirements.

```
Have single-modality scRNA-seq counts?
|
+-- No cell-type labels, want batch correction/integration -> scVI
+-- Have partial/full cell-type labels -> scANVI (semi-supervised; also
|                                          the entry point for label transfer)
|
Have multi-modal data?
+-- CITE-seq (RNA + surface protein, e.g. antibody-derived tags) -> totalVI
+-- Multiome (RNA + ATAC from the same cells) -> MultiVI
+-- scATAC-seq only (peak counts, no RNA) -> PeakVI
|
Have spatial transcriptomics + a matched scRNA-seq reference?
+-- Want per-spot cell-type proportions -> DestVI (two-stage: fit on
|                                          reference, then deconvolve spots;
|                                          see multimodal_workflows.md)
|
Have spliced/unspliced count layers (velocyto/kallisto|bustools output)?
+-- Want RNA velocity with uncertainty estimates -> veloVI
|
Already have a trained scVI/scANVI reference model and a NEW unlabeled
dataset to map onto it?
+-- Reference mapping / label transfer -> scANVI + scArches-style
                                           load_query_data (transfer_labels.py)
```

## Model -> use case -> minimum data

| Model | Primary use case | Minimum data | Script |
|-------|-------------------|--------------|--------|
| scVI | Unsupervised batch correction, denoising, general latent space | Raw counts, one `batch_key` column (optional but recommended) | `train_model.py --model scvi` |
| scANVI | Semi-supervised integration, label transfer | scVI's requirements + a `label_key` column (partial labels OK; use `unlabeled_category`) | `train_model.py --model scanvi` |
| totalVI | Joint RNA + protein modeling (CITE-seq) | Raw RNA counts + a protein-count matrix in `adata.obsm` | `train_model.py --model totalvi --protein-obsm <key>` |
| PeakVI | scATAC-seq accessibility | Raw peak-by-cell binary/count matrix | `train_model.py --model peakvi` |
| MultiVI | Joint RNA + ATAC (multiome) | Concatenated gene + peak features with a `var['modality']` column distinguishing them | `train_model.py --model multivi` |
| DestVI | Spatial cell-type deconvolution | A single-cell reference with cell-type labels AND a spatial (Visium-style) count matrix | See `multimodal_workflows.md` |
| veloVI | RNA velocity with uncertainty | `spliced` / `unspliced` count layers | `train_model.py --model velovi` |

## Decision shortcuts

- **Not sure if you need deep learning at all?** If you only need clustering,
  markers, and standard QC on a single dataset with no batch effect to
  correct, use `tooluniverse-single-cell` instead -- it is faster and does
  not require training a neural network.
- **Already ran Harmony in `tooluniverse-single-cell`?** scVI is a stronger
  batch-correction method for datasets with strong, nonlinear batch effects
  (e.g., across sequencing technologies), at the cost of GPU/CPU training
  time. If Harmony's result already looks clean on UMAP, you likely do not
  need to re-integrate with scVI.
- **Multiple candidate models fit?** Run `validate_adata.py --suggest` --
  it inspects `obs`/`obsm` for batch/label/protein/ATAC columns and
  recommends the most specific applicable model (e.g. totalVI over scVI if a
  protein matrix is present).
