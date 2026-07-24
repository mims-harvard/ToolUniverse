# Harmony Remote Tool (MCP Server)

Serves [Harmony](https://portals.broadinstitute.org/harmony/) (Korsunsky et al., *Nature Methods* 2019) — the default single-cell batch-integration baseline — as a ToolUniverse remote tool: `run_harmony_integrate` (batch-corrected PCA embedding).

Harmony corrects batch/sample effects on a low-dimensional PCA embedding via iterative batch-aware soft clustering and linear correction. The corrected embedding (`X_pca_harmony`) is the standard input to neighbor graphs / clustering / UMAP. It is fast and CPU-friendly even on large datasets.

Served remotely (not bundled) because it pulls in `harmonypy` + `scanpy`/`anndata`.

## Deploy

```bash
pip install -r requirements.txt          # harmonypy + scanpy
python harmony_tool.py                     # starts the MCP server on 127.0.0.1:8026
```

Inputs are referenced by `adata_path` (a server-accessible `.h5ad` AnnData),
since single-cell matrices are large. If `obsm['X_pca']` is already present it
is reused; otherwise PCA is computed (log-normalizing first when the matrix
looks like raw counts). Expose remotely only behind `TOOLUNIVERSE_API_TOKEN`
(SMCP bind guard).

## Register in ToolUniverse

Tool definition: `src/tooluniverse/data/remote_tools/harmony_tools.json`
(`type: RemoteTool`). Connect via the standard `MCPAutoLoaderTool`/`server_url`
mechanism.
