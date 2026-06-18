"""
scVI single-cell integration & differential expression — MCP Server.

scVI (single-cell Variational Inference; Lopez et al., Nature Methods 2018;
scvi-tools platform: Gayoso et al., Nature Biotechnology 2022) is a deep
generative model for scRNA-seq. It learns a low-dimensional, batch-corrected
latent representation of cells from raw UMI counts and supports Bayesian
differential expression.

This module exposes scVI as a ToolUniverse *remote* tool because it carries a
heavy deep-learning dependency stack (`scvi-tools` -> PyTorch + Lightning +
Pyro + scanpy/anndata). Running it on a dedicated server keeps the core
ToolUniverse install light; the model trains on CPU for small datasets and on
GPU for large ones.

Inputs are referenced by an ``adata_path`` (a server-accessible ``.h5ad`` of
raw counts) rather than inlined, because single-cell matrices are large.

Two operations are served:
  * run_scvi_integration            -> batch-corrected latent representation
  * run_scvi_differential_expression-> Bayesian DE between two cell groups

References
----------
Lopez R, Regier J, Cole MB, Jordan MI, Yosef N. "Deep generative modeling for
single-cell transcriptomics." Nature Methods 15, 1053-1058 (2018).
Gayoso A, Lopez R, Xing G, et al. "A Python library for probabilistic analysis
of single-cell omics data." Nature Biotechnology 40, 163-166 (2022).
"""

from typing import Any, Dict

import scanpy as sc
import scvi

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server


def _prepare_adata(adata_path: str, n_top_genes: int, layer_counts: str = "counts"):
    """Load an .h5ad of raw counts, preserve counts, select highly-variable genes."""
    adata = sc.read_h5ad(adata_path)
    if layer_counts not in adata.layers:
        adata.layers[layer_counts] = adata.X.copy()
    if n_top_genes and n_top_genes < adata.n_vars:
        sc.pp.highly_variable_genes(
            adata,
            n_top_genes=n_top_genes,
            subset=True,
            flavor="seurat_v3",
            layer=layer_counts,
        )
    return adata


def _train_scvi(adata, batch_key, n_latent, max_epochs, accelerator):
    """setup_anndata -> SCVI -> train; return the fitted model."""
    scvi.model.SCVI.setup_anndata(
        adata, layer="counts", batch_key=batch_key if batch_key else None
    )
    model = scvi.model.SCVI(adata, n_latent=n_latent)
    model.train(max_epochs=max_epochs, accelerator=accelerator)
    return model


@register_mcp_tool(
    tool_type_name="run_scvi_integration",
    config={
        "description": (
            "Train scVI on a single-cell RNA-seq count matrix and return the "
            "batch-corrected low-dimensional latent representation of cells "
            "(the standard input to clustering/UMAP). Corrects batch effects "
            "when a batch key is supplied."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "adata_path": {
                    "type": "string",
                    "description": "Server-accessible path or URL to an .h5ad AnnData of RAW UMI counts.",
                },
                "batch_key": {
                    "type": "string",
                    "description": "obs column naming the batch/sample for integration (optional; empty = no batch correction).",
                },
                "n_latent": {
                    "type": "integer",
                    "description": "Latent dimensionality (default 10).",
                },
                "max_epochs": {
                    "type": "integer",
                    "description": "Training epochs (default: scVI heuristic = min(round(20000/n_cells*400), 400)).",
                },
                "n_top_genes": {
                    "type": "integer",
                    "description": "Subset to this many highly-variable genes before training (default 2000; 0 = use all).",
                },
                "accelerator": {
                    "type": "string",
                    "description": "'auto' (default), 'cpu', or 'gpu'.",
                },
            },
            "required": ["adata_path"],
        },
    },
    mcp_config={
        "server_name": "scVI Single-Cell MCP Server",
        "host": "127.0.0.1",
        "port": 8010,
        "transport": "http",
    },
)
class ScviIntegrationTool:
    """Train scVI and return the batch-corrected latent representation."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        adata_path = arguments.get("adata_path")
        if not adata_path:
            return {"error": "Missing required parameter: adata_path"}
        batch_key = arguments.get("batch_key") or None
        n_latent = int(arguments.get("n_latent") or 10)
        n_top_genes = arguments.get("n_top_genes")
        n_top_genes = 2000 if n_top_genes is None else int(n_top_genes)
        max_epochs = arguments.get("max_epochs")
        max_epochs = int(max_epochs) if max_epochs else None
        accelerator = arguments.get("accelerator") or "auto"

        adata = _prepare_adata(adata_path, n_top_genes)
        model = _train_scvi(adata, batch_key, n_latent, max_epochs, accelerator)
        latent = model.get_latent_representation()
        return {
            "model": "scVI",
            "n_cells": int(latent.shape[0]),
            "n_latent": int(latent.shape[1]),
            "latent_representation": latent.tolist(),
            "cell_ids": adata.obs_names.astype(str).tolist(),
            "batch_key": batch_key,
        }


@register_mcp_tool(
    tool_type_name="run_scvi_differential_expression",
    config={
        "description": (
            "Train scVI on a single-cell count matrix and run Bayesian "
            "differential expression between two groups of cells, returning "
            "log-fold-changes and probabilities of differential expression."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "adata_path": {
                    "type": "string",
                    "description": "Server-accessible path or URL to an .h5ad AnnData of RAW UMI counts.",
                },
                "groupby": {
                    "type": "string",
                    "description": "obs column defining the groups to compare (e.g. 'cell_type').",
                },
                "group1": {
                    "type": "string",
                    "description": "Value in `groupby` for the foreground group.",
                },
                "group2": {
                    "type": "string",
                    "description": "Value in `groupby` for the reference group (optional; default = rest).",
                },
                "batch_key": {
                    "type": "string",
                    "description": "obs column naming the batch/sample (optional).",
                },
                "max_epochs": {
                    "type": "integer",
                    "description": "Training epochs (default: scVI heuristic).",
                },
            },
            "required": ["adata_path", "groupby", "group1"],
        },
    },
    mcp_config={
        "server_name": "scVI Single-Cell MCP Server",
        "host": "127.0.0.1",
        "port": 8010,
        "transport": "http",
    },
)
class ScviDifferentialExpressionTool:
    """Train scVI and run Bayesian differential expression between two groups."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        adata_path = arguments.get("adata_path")
        groupby = arguments.get("groupby")
        group1 = arguments.get("group1")
        if not (adata_path and groupby and group1):
            return {
                "error": "Missing required parameter(s): adata_path, groupby, group1"
            }
        group2 = arguments.get("group2") or None
        batch_key = arguments.get("batch_key") or None
        max_epochs = arguments.get("max_epochs")
        max_epochs = int(max_epochs) if max_epochs else None

        adata = _prepare_adata(adata_path, n_top_genes=0)
        model = _train_scvi(adata, batch_key, 10, max_epochs, "auto")
        de = model.differential_expression(
            groupby=groupby, group1=group1, group2=group2
        )
        de = de.reset_index().rename(columns={"index": "gene"})
        return {
            "model": "scVI",
            "groupby": groupby,
            "group1": group1,
            "group2": group2 or "rest",
            "n_genes": int(de.shape[0]),
            "differential_expression": de.to_dict(orient="records"),
        }


if __name__ == "__main__":
    start_mcp_server()
