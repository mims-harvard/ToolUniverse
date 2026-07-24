# scVelo Remote Tool (MCP Server)

Serves [scVelo](https://scvelo.readthedocs.io/)
(RNA velocity; Bergen et al., *Nature Biotechnology* 2020) as a ToolUniverse
remote tool: `run_scvelo_velocity` — infers RNA velocity from spliced/unspliced
mRNA and returns a velocity-derived pseudotime ordering of cells plus a per-cell
velocity confidence, and (with a `cluster_key`) the mean pseudotime per cluster
as a coarse trajectory ordering.

Served remotely (not bundled) because `scvelo` pulls in scanpy + anndata +
numba. The input `.h5ad` **must** carry `spliced` and `unspliced` count layers
(e.g. from velocyto, kb-python / kallisto|bustools, or STARsolo); without them
RNA velocity cannot be estimated and the tool returns a clear error.

## Deploy

```bash
pip install -r requirements.txt          # scvelo + scanpy + anndata
python scvelo_tool.py                      # starts the MCP server on 127.0.0.1:8025
```

Pipeline: `scv.pp.filter_and_normalize` -> `scv.pp.moments` -> `scv.tl.velocity`
-> `scv.tl.velocity_graph` -> `scv.tl.velocity_pseudotime` +
`scv.tl.velocity_confidence`.

Inputs are referenced by `adata_path` (a server-accessible `.h5ad` with
spliced/unspliced layers), since single-cell matrices are large. Only bounded
summaries (mean/min/max/std, per-cluster means) are returned; full per-cell
arrays are included only for small datasets (n_cells <= 500). Expose remotely
only behind `TOOLUNIVERSE_API_TOKEN` (SMCP bind guard).

## Register in ToolUniverse

Tool definition: `src/tooluniverse/data/remote_tools/scvelo_tools.json`
(`type: RemoteTool`). Connect via the standard `MCPAutoLoaderTool`/`server_url`
mechanism.
