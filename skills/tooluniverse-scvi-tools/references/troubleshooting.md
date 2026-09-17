# scvi-tools Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'scvi'` | scvi-tools not installed | `pip install scvi-tools`. This is a large install (pulls in PyTorch, PyTorch Lightning); on a CPU-only machine this is still fine but slower to train. |
| `ValueError: ... does not look like raw integer counts` (raised by our own `require_raw_counts` check) | You passed normalized/log data instead of raw counts | Re-run `prepare_data.py` on the ORIGINAL raw file, or pass `--layer` pointing at wherever raw counts actually live. Never bypass this check by renaming a normalized layer to `counts` -- scvi-tools' likelihood model assumes count data and silently produces meaningless results on continuous input. |
| Training runs but ELBO is flat / does not improve | Learning rate or `n_latent` mismatched to data size; or batch_key column is degenerate (all one value) | Check `validate_adata.py --batch-key <key>` reports >=2 batches. Try `n_latent=5-8` on small datasets (<5k cells). |
| Training loss becomes `NaN` | Extreme outlier cells/genes not filtered by QC; float overflow | Re-run `tooluniverse-single-cell`'s QC pass first; make sure genes with zero counts everywhere were removed (`min_cells` filter in `prepare_data.py`). |
| CUDA out of memory | Batch size too large for GPU, or too many cells for available VRAM | Reduce `plan_kwargs={"batch_size": ...}` when constructing the model (not currently a CLI flag here -- edit the relevant `train_*` function in `scripts/train_model.py`), or train on CPU with a smaller `--max-epochs` for a first pass. |
| No GPU detected, training is slow | Expected on CPU-only machines | Use `--max-epochs` to cap training for iteration; for a full production run, use a GPU machine or `setup-scvi-remote-tool` / `setup-scanvi-remote-tool` to run the equivalent training on a remote GPU-backed ToolUniverse tool. |
| `KeyError` on `--batch-key` / `--label-key` / `--protein-obsm` | Column/key name typo, or wrong AnnData object (e.g. passed the reference instead of the prepared file) | Run `validate_adata.py <file> --batch-key <key> --label-key <key>` first -- it reports missing keys before training starts instead of failing mid-run. |
| `transfer_labels.py` warns "fewer than half of the reference's genes are present in the query" | Query was HVG-selected independently, or profiled with a different panel | Re-run `prepare_data.py` on both reference and query using the SAME `--n-hvgs` and, ideally, restrict both to their shared gene intersection before selecting HVGs. |
| MultiVI: wrong `n_genes`/`n_regions` split, model trains but embeddings are nonsensical | Input AnnData lacks (or has a wrong) `var['modality']` column | Add `var['modality']` explicitly (`"Gene Expression"` / `"Peaks"`) before calling `prepare_data.py` -- do not rely on feature-name heuristics. |
| DestVI stage 2 (`DestVI.from_rna_model`) raises a gene-mismatch error | Spatial and single-cell reference gene panels differ | Subset both AnnData objects to their shared genes before Stage 1. |
| Differential expression output has no `is_de_fdr_0.05` column | Older/newer scvi-tools version changed the DE dataframe's column names | Inspect `de_df.columns` directly; the underlying `mean_lfc`, `bayes_factor`, and `proba_de` columns are stable across versions even when convenience columns are renamed. |

## When something looks wrong but no error is raised

scvi-tools will happily train on badly-prepared data without crashing --
a flat ELBO or a UMAP that mixes cell types together (not just batches) is
often the only sign. Always visualize the trained latent space colored by
both `batch_key` (should mix) and known marker genes / existing cluster
labels (should still separate) before reporting results.
