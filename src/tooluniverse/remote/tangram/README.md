# Tangram Remote Tool (MCP Server)

Serves [Tangram](https://tangram-sc.readthedocs.io/) (Biancalani et al., *Nature Methods* 2021) — alignment of single-cell RNA-seq onto spatial transcriptomics — as a ToolUniverse remote tool: `run_tangram_deconvolution`, which maps cell-type clusters from a single-cell reference onto a spatial assay and returns per-spot cell-type proportions (spatial deconvolution).

Served remotely (not bundled) because `tangram-sc` pulls in PyTorch + scanpy. Mapping runs on CPU for the modest reference/spatial matrices typical of this workflow.

## Deploy

```bash
pip install -r requirements.txt          # tangram-sc + scanpy
python tangram_tool.py                     # starts the MCP server on 127.0.0.1:8018
```

Inputs are referenced by paths (`sc_path`, `sp_path`): server-accessible `.h5ad`
files for the single-cell reference (with `cluster_label` in `obs`) and the
spatial assay. Expose remotely only behind `TOOLUNIVERSE_API_TOKEN`
(SMCP bind guard).

## Register in ToolUniverse

Tool definition: `src/tooluniverse/data/remote_tools/tangram_tools.json`
(`type: RemoteTool`). Connect via the standard `MCPAutoLoaderTool`/`server_url`
mechanism.
