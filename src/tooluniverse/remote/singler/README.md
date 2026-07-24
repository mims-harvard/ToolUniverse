# SingleR Remote Tool (MCP Server)

Serves [SingleR](https://bioconductor.org/packages/SingleR/) (Aran et al., *Nature Immunology* 2019) — reference-based single-cell annotation — as the ToolUniverse remote tool `run_singler_annotate`.

SingleR labels **each cell** (not each cluster) by correlating its expression against a labeled reference transcriptome and assigning the best-matching cell type. It is the standard automated alternative to manual marker-gene annotation.

Served remotely because the engine is **R/Bioconductor** (`SingleR` + `celldex`). The Python side reads the query `.h5ad` with scanpy and hands the matrix to the bundled `singler_annotate.R` over a MatrixMarket interchange — **no zellkonverter/basilisk required** (the heavy R↔Python bridge is avoided).

Two reference modes:

- **built-in** — a `celldex` panel by name (`HumanPrimaryCellAtlasData`, `BlueprintEncodeData`, `MonacoImmuneData`, `DatabaseImmuneCellExpressionData`, `NovershternHematopoieticData`, `ImmGenData`, `MouseRNAseqData`), downloaded on the server.
- **bring-your-own** — a labeled reference `.h5ad` (`ref_adata_path` + `ref_labels_key`).

Supply log-normalized expression for both query and reference (SingleR's default assumption).

## Deploy

```bash
pip install -r requirements.txt            # scanpy + scipy (Python side)
Rscript -e 'BiocManager::install(c("SingleR","celldex","jsonlite"))'   # R side
python singler_tool.py                      # starts the MCP server on 127.0.0.1:8029
```

`Rscript` must be on `PATH` (or set `RSCRIPT_BIN`). Expose remotely only behind
`TOOLUNIVERSE_API_TOKEN` (SMCP bind guard).

## Register in ToolUniverse

Tool definition: `src/tooluniverse/data/remote_tools/singler_tools.json`
(`type: RemoteTool`).
