# cell2location Remote Tool (MCP Server)

Serves [cell2location](https://cell2location.readthedocs.io/) (Kleshchevnikov et al., *Nature Biotechnology* 2022) — Bayesian cell-type deconvolution of spatial transcriptomics — as the ToolUniverse remote tool `run_cell2location_deconvolution`.

cell2location is a **two-step** model: (1) a negative-binomial `RegressionModel` estimates per-cell-type reference signatures from an annotated single-cell/single-nucleus reference, then (2) `Cell2location` maps those signatures onto spatial data (e.g. 10x Visium) to estimate absolute cell-type abundance at every spot.

Served remotely (not bundled) because `cell2location` pulls in scvi-tools + PyTorch + Lightning + Pyro + scanpy. **GPU-recommended**: training is slow on CPU, so `ref_epochs` and `sp_epochs` default LOW (250 each). Raise them on a GPU for production-quality posteriors.

## Deploy

```bash
pip install -r requirements.txt          # cell2location + scanpy + anndata
python cell2location_tool.py             # starts the MCP server on 127.0.0.1:8019
```

Inputs are referenced by `sc_path` (annotated reference `.h5ad` of raw counts)
and `sp_path` (spatial `.h5ad` of raw counts), since single-cell/spatial
matrices are large. Expose remotely only behind `TOOLUNIVERSE_API_TOKEN` (SMCP
bind guard).

## Register in ToolUniverse

Tool definition: `src/tooluniverse/data/remote_tools/cell2location_tools.json`
(`type: RemoteTool`). Connect via the standard `MCPAutoLoaderTool`/`server_url`
mechanism.
