# Borzoi Remote Tool (MCP Server)

Serves [Borzoi](https://www.nature.com/articles/s41588-024-02053-6) (Linder et al., *Nature Genetics* 2025) — sequence → RNA-seq/multi-omic coverage prediction, the successor to Enformer — as ToolUniverse remote tools: `run_borzoi_predict` and `run_borzoi_variant_effect`.

Served remotely (not bundled) because it needs PyTorch + ~0.8 GB of weights per replicate (`johahi/borzoi-replicate-{0..3}`) and is GPU-recommended.

## Deploy

```bash
pip install -r requirements.txt          # torch + borzoi-pytorch
python borzoi_tool.py                      # starts the MCP server on 127.0.0.1:8012
```

Expose remotely only behind `TOOLUNIVERSE_API_TOKEN` (SMCP bind guard).

## Register in ToolUniverse

Tool definitions: `src/tooluniverse/data/remote_tools/borzoi_tools.json`
(`type: RemoteTool`). Connect via the standard `MCPAutoLoaderTool`/`server_url`
mechanism. First call lazily downloads and caches the weights.
