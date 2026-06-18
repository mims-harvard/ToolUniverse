# scVI Remote Tool (MCP Server)

Serves [scVI](https://www.nature.com/articles/s41592-018-0229-2) (Lopez et al., *Nature Methods* 2018; [scvi-tools](https://www.nature.com/articles/s41587-021-01206-w), Gayoso et al., *Nature Biotechnology* 2022) — probabilistic single-cell RNA-seq modeling — as ToolUniverse remote tools: `run_scvi_integration` (batch-corrected latent representation) and `run_scvi_differential_expression`.

Served remotely (not bundled) because `scvi-tools` pulls in PyTorch + Lightning + Pyro + scanpy. Small datasets train on CPU; large ones benefit from a GPU.

## Deploy

```bash
pip install -r requirements.txt          # scvi-tools + scanpy
python scvi_tool.py                        # starts the MCP server on 127.0.0.1:8010
```

Inputs are referenced by `adata_path` (a server-accessible `.h5ad` of raw UMI
counts), since single-cell matrices are large. Expose remotely only behind
`TOOLUNIVERSE_API_TOKEN` (SMCP bind guard).

## Register in ToolUniverse

Tool definitions: `src/tooluniverse/data/remote_tools/scvi_tools.json`
(`type: RemoteTool`). Connect via the standard `MCPAutoLoaderTool`/`server_url`
mechanism.
