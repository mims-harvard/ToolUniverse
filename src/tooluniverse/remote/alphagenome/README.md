# AlphaGenome Remote Tool (MCP Server)

Serves [AlphaGenome](https://deepmind.google.com/science/alphagenome) (Avsec et al., *Nature* 2026) — DeepMind's hosted successor to Enformer/Borzoi — as the ToolUniverse remote tools `run_alphagenome_score_variant` and `run_alphagenome_predict_interval`.

AlphaGenome is a single DNA-sequence model that predicts multimodal genomic tracks (RNA-seq, CAGE, ATAC, DNase, histone/TF ChIP, splicing, contact maps) over up to **1 Mb at single-base resolution**, and scores regulatory variant effects.

It is a **hosted API** reached over gRPC through the official `alphagenome` Python SDK. Served remotely so the **SDK dependency and the `ALPHA_GENOME_API_KEY` credential live on the server**, keeping the core ToolUniverse install light (the SDK is not a core dependency). Free for non-commercial use.

## Operations

- `run_alphagenome_score_variant` — recommended ref-vs-alt per-track variant-effect scores (sorted by |effect|).
- `run_alphagenome_predict_interval` — compact per-modality track summary (counts + shapes) for an interval.

## Deploy

```bash
pip install -r requirements.txt            # alphagenome SDK
export ALPHA_GENOME_API_KEY=...             # free non-commercial key (link above)
python alphagenome_tool.py                  # starts the MCP server on 127.0.0.1:8033
```

Expose remotely only behind `TOOLUNIVERSE_API_TOKEN` (SMCP bind guard).

## Register in ToolUniverse

Tool definition: `src/tooluniverse/data/remote_tools/alphagenome_tools.json` (`type: RemoteTool`).
