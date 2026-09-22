---
name: tooluniverse-scvi-tools
description: Deep learning for single-cell omics using scvi-tools — probabilistic (VAE-based) batch correction and integration with scVI, semi-supervised integration and label transfer with scANVI, CITE-seq RNA+protein joint modeling with totalVI, scATAC-seq analysis with PeakVI, multiome RNA+ATAC joint modeling with MultiVI, spatial transcriptomics cell-type deconvolution with DestVI, and RNA velocity with veloVI. Use when scVI, scANVI, totalVI, PeakVI, MultiVI, DestVI, or veloVI are mentioned by name, or when a request needs deep-learning-based batch correction, reference mapping / scArches-style query-to-reference mapping, denoising single-cell counts, joint modeling of two modalities (RNA+protein, RNA+ATAC, single-cell+spatial), or a variational-autoencoder latent space for single-cell data — as opposed to classic scanpy/Harmony-based integration.
disable-model-invocation: true
---

# scvi-tools Deep Learning for Single-Cell Omics

Local, guided workflows for training and applying scvi-tools' probabilistic
deep-learning models on a user's own AnnData files.

## Honesty contract (read first)

This skill trains real neural networks via the real `scvi-tools` package. It
must never fabricate a latent space, a training curve, or a DE result.

1. **Preflight before anything.** Every script checks `import scvi` (and
   `anndata`/`scanpy`/`numpy`) before touching data. If scvi-tools is not
   installed, the script prints the exact `pip install scvi-tools` command
   and exits 0 — it does not estimate, guess, or describe hypothetical
   training results.
2. **Raw integer counts required.** Every training script verifies the input
   layer looks like raw counts and refuses to train on normalized/log data
   with a clear error, rather than letting scvi-tools fail deep inside
   training or silently produce meaningless output.
3. **Report the device honestly.** Every script prints whether it is
   training on GPU (CUDA/MPS) or CPU before starting, since CPU training can
   be 10-50x slower — never claim GPU training happened when it did not.
4. **Never overwrite the input file.** All outputs go to a separate
   directory/file passed by the caller.

## When to Use This Skill

Use when the user:
- Names scVI, scANVI, totalVI, PeakVI, MultiVI, DestVI, veloVI, or scArches
  specifically
- Wants deep-learning-based batch correction / integration for scRNA-seq
  with strong or nonlinear batch effects
- Has CITE-seq (RNA + surface protein), multiome (RNA + ATAC), or
  spatial + single-cell reference data and wants a joint/deconvolved model
- Wants to map a new (query) dataset onto an existing trained reference
  model (reference mapping / label transfer)
- Wants RNA velocity with model-based uncertainty (not just `scvelo`'s
  point estimates)

**NOT for** (use other skills instead):
- Plain scanpy-based QC, normalization, clustering, marker genes, or
  Harmony batch correction with no deep learning involved ->
  `tooluniverse-single-cell`
- Running scVI or scANVI as a shared, remote GPU-backed MCP tool for other
  callers (not local, guided analysis of your own file) ->
  `setup-scvi-remote-tool` / `setup-scanvi-remote-tool`
- Bulk RNA-seq DESeq2 -> `tooluniverse-rnaseq-deseq2`
- FASTQ-level QC/trimming -> `tooluniverse-fastq-qc`

## Model Selection

See `references/model_selection.md` for the full decision tree. Quick
version:

| Data | Model |
|---|---|
| scRNA-seq, no labels, want integration | scVI |
| scRNA-seq, partial/full cell-type labels | scANVI |
| CITE-seq (RNA + protein) | totalVI |
| scATAC-seq only | PeakVI |
| Multiome (RNA + ATAC) | MultiVI |
| Spatial + single-cell reference | DestVI |
| RNA velocity (spliced/unspliced) | veloVI |
| Map new data onto an existing reference | scANVI + `load_query_data` |

Run `python scripts/validate_adata.py your.h5ad --batch-key batch --suggest`
to get a data-driven recommendation instead of guessing.

## Workflow

```bash
# 1. Check the environment and the data
python scripts/validate_adata.py raw.h5ad --batch-key batch --suggest

# 2. Prepare: QC, HVG selection, stash raw counts in a 'counts' layer
python scripts/prepare_data.py raw.h5ad prepared.h5ad --batch-key batch

# 3. Train the model chosen in step 1
python scripts/train_model.py prepared.h5ad results/ --model scvi --batch-key batch

# 4. Differential expression (posterior-based, not scanpy's rank_genes_groups)
python scripts/differential_expression.py results/scvi_model results/adata_scvi_trained.h5ad \
    de.csv --groupby leiden

# 5. (Optional) Map a new dataset onto a trained scANVI reference
python scripts/transfer_labels.py results/scanvi_model prepared.h5ad query.h5ad results/
```

For totalVI/MultiVI/DestVI's modality-specific input shapes, and DestVI's
two-stage fit, see `references/multimodal_workflows.md` — do not guess the
input format; getting it wrong is the most common failure mode for these
three models.

## Reference Documentation

- `references/model_selection.md` — full decision tree, minimum data per model
- `references/scrna_integration.md` — scVI/scANVI integration details, when to prefer this over Harmony
- `references/multimodal_workflows.md` — totalVI, MultiVI, DestVI input shapes and the DestVI two-stage fit
- `references/troubleshooting.md` — install issues, NaN losses, GPU/OOM, key mismatches, silent-failure checklist
