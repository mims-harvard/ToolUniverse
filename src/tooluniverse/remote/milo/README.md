# Milo Remote Tool (MCP Server)

Serves [Milo](https://www.nature.com/articles/s41587-021-01033-z) (Dann et al.,
*Nature Biotechnology* 2022) — single-cell **differential abundance** testing on
kNN-graph neighbourhoods — as a ToolUniverse remote tool:
`run_milo_differential_abundance`.

Milo assigns cells to overlapping neighbourhoods on a kNN graph, counts cells
per neighbourhood per biological sample, and fits a negative-binomial GLM to
test each neighbourhood for a shift in abundance across a condition, reporting a
log-fold-change and a spatially-corrected FDR (SpatialFDR) per neighbourhood.

Served remotely (not bundled) because Milo's current implementation lives in
[`pertpy`](https://pertpy.readthedocs.io/) (`pt.tl.Milo`), which pulls in
scanpy + mudata + pyDESeq2/edgeR. The standalone `milopy` package is supported
as a fallback.

## Deploy

```bash
pip install -r requirements.txt          # pertpy + scanpy
python milo_tool.py                        # starts the MCP server on 127.0.0.1:8023
```

Inputs are referenced by `adata_path` (a server-accessible `.h5ad`), since
single-cell matrices are large. The `.h5ad` must have a `sample_col` (biological
replicate id) and a `condition_col` (the condition being tested) in `adata.obs`.
Expose remotely only behind `TOOLUNIVERSE_API_TOKEN` (SMCP bind guard).

## Register in ToolUniverse

Tool definition: `src/tooluniverse/data/remote_tools/milo_tools.json`
(`type: RemoteTool`). Connect via the standard `MCPAutoLoaderTool`/`server_url`
mechanism.
