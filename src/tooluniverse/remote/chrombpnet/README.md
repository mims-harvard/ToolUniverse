# ChromBPNet Remote Tool (MCP Server)

Serves [ChromBPNet](https://github.com/kundajelab/chrombpnet) (Pampari et al., *Nature Methods* 2025) — base-resolution, bias-corrected deep learning of chromatin accessibility from DNA sequence — as the ToolUniverse remote tools `run_chrombpnet_predict` and `run_chrombpnet_variant_effect`.

ChromBPNet predicts ATAC-seq/DNase-seq accessibility from a 2,114 bp sequence with the Tn5/DNase enzyme bias regressed out. It is the modern successor to DeepSEA/Basset for **non-coding regulatory variant interpretation** (GWAS/eQTL fine-mapping) and TF-motif discovery, and underlies the ENCODE accessibility model zoo. The model has two output heads: a 1,000 bp accessibility *profile* (shape) and a scalar *log total count* (magnitude).

> Note on DeepSEA: the classic DeepSEA model (and HumanBase/FUMA front-ends) is browser-only with no maintained programmatic API. ChromBPNet is the maintained, installable, bias-corrected equivalent and is what this tool wraps.

Served remotely because it carries a heavy TensorFlow/Keras stack and requires a trained, **cell-type-specific** model (`.h5`), referenced per call by `model_path` on the server. Get models from the ChromBPNet model zoo / ENCODE, or train your own with the `chrombpnet` package.

## Operations

- `run_chrombpnet_predict` — predicted accessibility (log total counts + base-resolution profile) for one sequence.
- `run_chrombpnet_variant_effect` — ref-vs-alt **count log2 fold-change** (magnitude effect) + **profile Jensen-Shannon divergence** (shape effect), the canonical ChromBPNet variant scores.

## Models

Trained, cell-type-specific models live in the **HF ENCODE ChromBPNet zoo** — e.g. [`kundajelab/encode-chrombpnet-DNASE-ENCSR000EMK-ENCSR816AQM`](https://huggingface.co/kundajelab/encode-chrombpnet-DNASE-ENCSR000EMK-ENCSR816AQM). Each repo has 5 folds; use the bias-corrected `fold_N/model.chrombpnet_nobias.fold_N.*.h5` for variant scoring. Pull one with `huggingface_hub.hf_hub_download(...)` and pass the path as `model_path`.

## Deploy

```bash
pip install -r requirements.txt             # tensorflow + tf-keras + numpy + huggingface_hub
export TF_USE_LEGACY_KERAS=1                 # ENCODE zoo models are Keras 2 (.h5)
python chrombpnet_tool.py                    # starts the MCP server on 127.0.0.1:8032
```

`TF_USE_LEGACY_KERAS=1` + `tf-keras` are required on TensorFlow ≥ 2.16 (Keras 3) so
`load_model` can read the legacy Keras-2 `.h5`. GPU recommended. Expose remotely only
behind `TOOLUNIVERSE_API_TOKEN` (SMCP bind guard).

> **Validated** end-to-end against a real ENCODE DNASE model
> (`kundajelab/encode-chrombpnet-DNASE-ENCSR000EMK`): the model's `(None, 2114, 4)`
> input and `[(None, 1000), (None, 1)]` outputs match the tool's `INPUT_LEN`/
> `OUTPUT_LEN` and head ordering; predict returns a valid accessibility distribution,
> and variant scoring scales correctly (identical → 0; a 50 bp disruption → larger
> count log2FC + profile JSD than a single SNP).

## Register in ToolUniverse

Tool definition: `src/tooluniverse/data/remote_tools/chrombpnet_tools.json`
(`type: RemoteTool`).
