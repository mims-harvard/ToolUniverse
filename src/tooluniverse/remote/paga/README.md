# PAGA Remote Tool (MCP Server)

Serves [PAGA](https://scanpy.readthedocs.io/en/stable/generated/scanpy.tl.paga.html)
(Partition-based Graph Abstraction; Wolf et al., *Genome Biology* 2019) as a
ToolUniverse remote tool: `run_paga_trajectory` — estimates connectivity between
single-cell clusters and reports the strongest cluster pairs (the trajectory
backbone).

Served remotely (not bundled) because PAGA pulls in `scanpy` + anndata + igraph +
leidenalg. Computation is cheap once a neighbors graph exists; if one is absent
the tool log-normalizes, runs PCA, and builds neighbors before `sc.tl.paga`.

## Deploy

```bash
pip install -r requirements.txt          # scanpy + igraph + leidenalg
python paga_tool.py                        # starts the MCP server on 127.0.0.1:8022
```

Inputs are referenced by `adata_path` (a server-accessible `.h5ad` whose `obs`
carries the requested `cluster_key`), since single-cell matrices are large. The
cluster x cluster connectivity matrix returned is small and bounded. Expose
remotely only behind `TOOLUNIVERSE_API_TOKEN` (SMCP bind guard).

## Register in ToolUniverse

Tool definition: `src/tooluniverse/data/remote_tools/paga_tools.json`
(`type: RemoteTool`). Connect via the standard `MCPAutoLoaderTool`/`server_url`
mechanism.
