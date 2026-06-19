# Scrublet Remote Tool (MCP Server)

Serves [Scrublet](https://github.com/swolock/scrublet) (Wolock et al., *Cell Systems* 2019) — single-cell RNA-seq doublet detection — as a ToolUniverse remote tool: `run_scrublet_doublets` (per-cell doublet scores + boolean predictions).

Served remotely (not bundled) because it pulls in the `scanpy`/`anndata` single-cell stack plus `scikit-image` for the KNN/UMAP machinery. Scrublet operates on **raw counts**, not normalized/log-transformed data.

## Deploy

```bash
pip install -r requirements.txt          # scanpy + scikit-image + anndata
python scrublet_tool.py                    # starts the MCP server on 127.0.0.1:8015
```

Inputs are referenced by `adata_path` (a server-accessible `.h5ad` of raw
counts), since single-cell matrices are large. Expose remotely only behind
`TOOLUNIVERSE_API_TOKEN` (SMCP bind guard).

## Register in ToolUniverse

Tool definition: `src/tooluniverse/data/remote_tools/scrublet_tools.json`
(`type: RemoteTool`). Connect via the standard `MCPAutoLoaderTool`/`server_url`
mechanism.
