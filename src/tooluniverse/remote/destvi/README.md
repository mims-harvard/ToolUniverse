# DestVI Remote Tool (MCP Server)

Serves [DestVI](https://www.nature.com/articles/s41587-022-01272-8) (Lopez et al., *Nature Biotechnology* 2022; [scvi-tools](https://www.nature.com/articles/s41587-021-01206-w), Gayoso et al., *Nature Biotechnology* 2022) — probabilistic deconvolution of spatial transcriptomics — as a ToolUniverse remote tool: `run_destvi_deconvolution`.

DestVI is a two-step model: a `CondSCVI` model learns per-cell-type expression profiles from an annotated single-cell RNA-seq reference, then a `DestVI` model (`from_rna_model`) is fit on the spatial slide and `get_proportions()` returns per-spot cell-type proportions.

Served remotely (not bundled) because `scvi-tools` pulls in PyTorch + Lightning + Pyro + scanpy. Small datasets train on CPU; large ones benefit from a GPU.

## Deploy

```bash
pip install -r requirements.txt          # scvi-tools + scanpy
python destvi_tool.py                      # starts the MCP server on 127.0.0.1:8020
```

Inputs are referenced by `sc_path` and `sp_path` (server-accessible `.h5ad`
files of raw counts), since single-cell and spatial matrices are large. The
single-cell reference must carry the `cluster_label` cell-type column in `obs`.
Expose remotely only behind `TOOLUNIVERSE_API_TOKEN` (SMCP bind guard).

## Register in ToolUniverse

Tool definition: `src/tooluniverse/data/remote_tools/destvi_tools.json`
(`type: RemoteTool`). Connect via the standard `MCPAutoLoaderTool`/`server_url`
mechanism.
