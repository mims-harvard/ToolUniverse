# ChromBPNet Remote Tool (MCP Server)

Serves [ChromBPNet](https://github.com/kundajelab/chrombpnet) (Pampari et al., *Nature Methods* 2025) — base-resolution, bias-corrected deep learning of chromatin accessibility from DNA sequence — as the ToolUniverse remote tools `run_chrombpnet_predict` and `run_chrombpnet_variant_effect`.

ChromBPNet predicts ATAC-seq/DNase-seq accessibility from a 2,114 bp sequence with the Tn5/DNase enzyme bias regressed out. It is the modern successor to DeepSEA/Basset for **non-coding regulatory variant interpretation** (GWAS/eQTL fine-mapping) and TF-motif discovery, and underlies the ENCODE accessibility model zoo. The model has two output heads: a 1,000 bp accessibility *profile* (shape) and a scalar *log total count* (magnitude).

> Note on DeepSEA: the classic DeepSEA model (and HumanBase/FUMA front-ends) is browser-only with no maintained programmatic API. ChromBPNet is the maintained, installable, bias-corrected equivalent and is what this tool wraps.

Served remotely because it carries a heavy TensorFlow/Keras stack and requires a trained, **cell-type-specific** model (`.h5`), referenced per call by `model_path` on the server. Get models from the ChromBPNet model zoo / ENCODE, or train your own with the `chrombpnet` package.

## Operations

- `run_chrombpnet_predict` — predicted accessibility (log total counts + base-resolution profile) for one sequence.
- `run_chrombpnet_variant_effect` — ref-vs-alt **count log2 fold-change** (magnitude effect) + **profile Jensen-Shannon divergence** (shape effect), the canonical ChromBPNet variant scores.

## Deploy

```bash
pip install -r requirements.txt            # tensorflow + numpy
python chrombpnet_tool.py                   # starts the MCP server on 127.0.0.1:8032
```

Stage trained model `.h5` files on the server and pass their paths as `model_path`.
GPU recommended. Expose remotely only behind `TOOLUNIVERSE_API_TOKEN` (SMCP bind guard).

## Register in ToolUniverse

Tool definition: `src/tooluniverse/data/remote_tools/chrombpnet_tools.json`
(`type: RemoteTool`).
