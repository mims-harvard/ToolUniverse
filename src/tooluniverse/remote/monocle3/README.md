# Monocle3 Remote Tool (MCP Server)

Serves [Monocle3](https://cole-trapnell-lab.github.io/monocle3/) (Cao et al., *Nature* 2019; Trapnell lab) — single-cell pseudotime / trajectory inference — as the ToolUniverse remote tool `run_monocle3_pseudotime`.

Monocle3 learns a **principal graph** through a UMAP embedding (capturing branches and loops) and orders cells in pseudotime from a chosen root. Unlike Slingshot (which orders pre-computed clusters), Monocle3 learns its own graph, and is the standard Trapnell-lab pseudotime tool.

Served remotely because the engine is **R/Bioconductor** (`monocle3`). The Python side reads the `.h5ad` with scanpy and hands the **raw count** matrix to the bundled `monocle3_pseudotime.R` (MatrixMarket interchange — no zellkonverter/basilisk). The R script runs the standard `new_cell_data_set → preprocess_cds → reduce_dimension → cluster_cells → learn_graph → order_cells` pipeline.

Root the trajectory with `root_cluster` (all cells of a named input cluster — requires `cluster_key`) or explicit `root_cells`.

## Deploy

```bash
pip install -r requirements.txt            # scanpy + scipy (Python side)
# R side — monocle3 needs Bioconductor deps + system libs (gdal/geos/proj via terra):
Rscript -e 'BiocManager::install(c("SingleCellExperiment","batchelor","terra","ggrastr","leidenbase"))'
Rscript -e 'remotes::install_github("cole-trapnell-lab/monocle3")'
python monocle3_tool.py                      # starts the MCP server on 127.0.0.1:8031
```

`Rscript` must be on `PATH` (or set `RSCRIPT_BIN`). Expose remotely only behind
`TOOLUNIVERSE_API_TOKEN` (SMCP bind guard).

## Register in ToolUniverse

Tool definition: `src/tooluniverse/data/remote_tools/monocle3_tools.json`
(`type: RemoteTool`).
