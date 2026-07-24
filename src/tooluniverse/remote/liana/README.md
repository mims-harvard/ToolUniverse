# LIANA Remote Tool (MCP Server)

Serves [LIANA](https://liana-py.readthedocs.io/) (Dimitrov et al., *Nature Communications* 2022) — the consensus cell-cell communication framework that re-implements CellPhoneDB / CellChat / NATMI / Connectome / SingleCellSignalR over shared curated ligand-receptor resources — as a ToolUniverse remote tool: `run_liana_cellphonedb` (top ligand-receptor interactions between cell types via the CellPhoneDB method).

Served remotely (not bundled) because `liana` pulls in scanpy + anndata + scikit-learn and the bundled ligand-receptor resources.

## Deploy

```bash
pip install -r requirements.txt          # liana + scanpy
python liana_tool.py                       # starts the MCP server on 127.0.0.1:8017
```

Inputs are referenced by `adata_path` (a server-accessible `.h5ad` of
log1p-normalized expression with a cell-type label column in `obs`), since
single-cell matrices are large. Expose remotely only behind
`TOOLUNIVERSE_API_TOKEN` (SMCP bind guard).

## Register in ToolUniverse

Tool definition: `src/tooluniverse/data/remote_tools/liana_tools.json`
(`type: RemoteTool`). Connect via the standard `MCPAutoLoaderTool`/`server_url`
mechanism.
