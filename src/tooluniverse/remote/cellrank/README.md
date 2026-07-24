# CellRank Remote Tool (MCP Server)

Serves [CellRank 2](https://cellrank.readthedocs.io/) (Weiler et al., *Nature Methods* 2024; original CellRank: Lange et al., *Nature Methods* 2022) — unified single-cell fate mapping — as the ToolUniverse remote tool `run_cellrank_fate`.

CellRank builds a Markov transition matrix over cells using a **kernel**, then coarse-grains it with a **GPCCA estimator** to find terminal macrostates and compute, for every cell, its probability of reaching each terminal state. The kernel is selectable:

- `connectivity` (default) — uses only the kNN graph, so it runs on any dataset (computed automatically if neighbors are absent).
- `pseudotime` — directs transitions along a precomputed pseudotime (`pseudotime_key` in `obs`, e.g. `dpt_pseudotime`).
- `velocity` — uses RNA velocity layers (requires scVelo-computed velocity).

Served remotely (not bundled) because `cellrank` pulls in scanpy/anndata + scikit-learn + pyGPCCA (+ scVelo for the velocity kernel). Small datasets run on CPU.

## Deploy

```bash
pip install -r requirements.txt          # cellrank + scanpy
python cellrank_tool.py                   # starts the MCP server on 127.0.0.1:8028
```

Input is referenced by `adata_path` (a server-accessible `.h5ad`), since
single-cell matrices are large. Expose remotely only behind
`TOOLUNIVERSE_API_TOKEN` (SMCP bind guard).

## Register in ToolUniverse

Tool definition: `src/tooluniverse/data/remote_tools/cellrank_tools.json`
(`type: RemoteTool`). Connect via the standard `MCPAutoLoaderTool`/`server_url`
mechanism.
