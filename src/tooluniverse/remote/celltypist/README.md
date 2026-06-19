# CellTypist Remote Tool (MCP Server)

Serves [CellTypist](https://www.celltypist.org/) (Domínguez Conde et al., *Science* 2022; Xu et al., *Cell* 2023) — automated single-cell type annotation — as a ToolUniverse remote tool: `run_celltypist_annotate` (per-cell predicted labels + cell-type counts).

Served remotely (not bundled) because `celltypist` pulls in scikit-learn + scanpy and downloads pre-trained model files on first use.

## Deploy

```bash
pip install -r requirements.txt          # celltypist + scanpy
python celltypist_tool.py                  # starts the MCP server on 127.0.0.1:8014
```

Inputs are referenced by `adata_path` (a server-accessible `.h5ad`), since
single-cell matrices are large. The matrix is log1p-normalised to 10,000 counts
per cell before annotation (CellTypist's expected input). Expose remotely only
behind `TOOLUNIVERSE_API_TOKEN` (SMCP bind guard).

## Models

`model` selects a CellTypist pre-trained model (default `Immune_All_Low.pkl`).
The full list of built-in models is at <https://www.celltypist.org/models>;
required model files are downloaded automatically.

## Register in ToolUniverse

Tool definitions: `src/tooluniverse/data/remote_tools/celltypist_tools.json`
(`type: RemoteTool`). Connect via the standard `MCPAutoLoaderTool`/`server_url`
mechanism.
