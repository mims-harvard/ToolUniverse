# scANVI Remote Tool (MCP Server)

Serves [scANVI](https://www.embopress.org/doi/full/10.15252/msb.20209620) (Xu et al., *Molecular Systems Biology* 2021; [scvi-tools](https://www.nature.com/articles/s41587-021-01206-w), Gayoso et al., *Nature Biotechnology* 2022) — semi-supervised single-cell annotation / reference label transfer — as the ToolUniverse remote tool `run_scanvi_annotate`.

scANVI extends scVI: it pretrains scVI on raw UMI counts, then refines the model semi-supervised on the cells that already carry a known label, and predicts a cell type for every cell. Use it to transfer labels onto the unlabeled cells of a partially-annotated dataset.

Served remotely (not bundled) because `scvi-tools` pulls in PyTorch + Lightning + Pyro + scanpy. Small datasets train on CPU; large ones benefit from a GPU.

## Deploy

```bash
pip install -r requirements.txt          # scvi-tools + scanpy
python scanvi_tool.py                       # starts the MCP server on 127.0.0.1:8027
```

Input is referenced by `adata_path` (a server-accessible `.h5ad` of raw UMI
counts), since single-cell matrices are large. The AnnData must carry a
`labels_key` obs column where some cells hold their known cell type and the
unlabeled cells hold the `unlabeled_category` sentinel (default `"Unknown"`).
Raw counts are preserved in a `counts` layer before training. Expose remotely
only behind `TOOLUNIVERSE_API_TOKEN` (SMCP bind guard).

## Register in ToolUniverse

Tool definition: `src/tooluniverse/data/remote_tools/scanvi_tools.json`
(`type: RemoteTool`). Connect via the standard `MCPAutoLoaderTool`/`server_url`
mechanism.
