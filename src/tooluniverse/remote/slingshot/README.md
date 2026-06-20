# Slingshot Remote Tool (MCP Server)

Serves [Slingshot](https://bioconductor.org/packages/slingshot/) (Street et al., *BMC Genomics* 2018) — single-cell lineage and pseudotime inference — as the ToolUniverse remote tool `run_slingshot_trajectory`.

Given a low-dimensional embedding and cluster labels, Slingshot builds a minimum spanning tree on the cluster centroids to order them into smooth lineages, fits simultaneous principal curves, and assigns each cell a pseudotime along every lineage it belongs to. It is robust for tree-shaped differentiation and a standard trajectory method.

Served remotely because the engine is **R/Bioconductor** (`slingshot`). The Python side reads the `.h5ad` with scanpy, extracts the chosen embedding (`obsm`) and cluster labels (`obs`), and hands them to the bundled `slingshot_trajectory.R` (CSV interchange — no zellkonverter/basilisk required).

Anchor directionality with `start_cluster` (the known root) and/or `end_clusters` (known terminal fates) when available — strongly recommended, since otherwise lineage orientation is arbitrary.

## Deploy

```bash
pip install -r requirements.txt            # scanpy + numpy (Python side)
Rscript -e 'BiocManager::install(c("slingshot","jsonlite"))'   # R side
python slingshot_tool.py                    # starts the MCP server on 127.0.0.1:8030
```

`Rscript` must be on `PATH` (or set `RSCRIPT_BIN`). Expose remotely only behind
`TOOLUNIVERSE_API_TOKEN` (SMCP bind guard).

## Register in ToolUniverse

Tool definition: `src/tooluniverse/data/remote_tools/slingshot_tools.json`
(`type: RemoteTool`).
