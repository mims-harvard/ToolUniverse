# Squidpy Remote Tool (MCP Server)

Serves [Squidpy](https://squidpy.readthedocs.io/) (Palla et al., *Nature Methods* 2022) — spatial single-cell omics analysis — as a ToolUniverse remote tool: `run_squidpy_nhood_enrichment`, which builds a spatial neighbors graph and runs the neighborhood-enrichment permutation test (which cell-type pairs co-localize vs. segregate).

Served remotely (not bundled) because `squidpy` pulls in scanpy/anndata + networkx + scikit-image + numba.

## Deploy

```bash
pip install -r requirements.txt          # squidpy + scanpy + anndata
python squidpy_tool.py                     # starts the MCP server on 127.0.0.1:8016
```

Inputs are referenced by `adata_path` (a server-accessible spatial `.h5ad` with
`adata.obsm["spatial"]` coordinates and the `cluster_key` column in
`adata.obs`), since spatial matrices are large. Expose remotely only behind
`TOOLUNIVERSE_API_TOKEN` (SMCP bind guard).

## Register in ToolUniverse

Tool definitions: `src/tooluniverse/data/remote_tools/squidpy_tools.json`
(`type: RemoteTool`). Connect via the standard `MCPAutoLoaderTool`/`server_url`
mechanism.
