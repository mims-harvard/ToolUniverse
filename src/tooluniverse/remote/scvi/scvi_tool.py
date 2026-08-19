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

import json
from typing import Any, Dict

import numpy as np
import scanpy as sc
import scvi

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server
from tooluniverse.remote_argument_validation import (
    bounded_integer,
    bounded_text,
    require_argument_object,
)
from tooluniverse.remote_data_path import load_remote_h5ad


_MAX_INLINE_CELLS = 5_000
_MAX_DE_GENES = 500


def _prepare_adata(adata_path: str, n_top_genes: int, layer_counts: str = "counts"):
    """Load an .h5ad of raw counts, preserve counts, select highly-variable genes."""
    adata = load_remote_h5ad(adata_path, sc.read_h5ad)
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
                    "description": "An .h5ad file of raw UMI counts inside the provider-configured data directory.",
                },
                "batch_key": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 128,
                    "description": "obs column naming the batch/sample for integration (optional; empty = no batch correction).",
                },
                "n_latent": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 128,
                    "description": "Latent dimensionality (default 10).",
                },
                "max_epochs": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 400,
                    "description": "Training epochs (default: scVI heuristic = min(round(20000/n_cells*400), 400)).",
                },
                "n_top_genes": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 20000,
                    "description": "Subset to this many highly-variable genes before training (default 2000; 0 = use all).",
                },
                "accelerator": {
                    "type": "string",
                    "enum": ["auto", "cpu", "gpu"],
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
        try:
            arguments = require_argument_object(arguments)
        except ValueError as exc:
            return {"error": str(exc)}
        adata_path = arguments.get("adata_path")
        if not adata_path:
            return {"error": "Missing required parameter: adata_path"}
        try:
            batch_key = bounded_text(arguments.get("batch_key"), "batch_key")
            n_latent = bounded_integer(
                arguments.get("n_latent"),
                "n_latent",
                default=10,
                minimum=1,
                maximum=128,
            )
            n_top_genes = bounded_integer(
                arguments.get("n_top_genes"),
                "n_top_genes",
                default=2000,
                minimum=0,
                maximum=20_000,
            )
            max_epochs = bounded_integer(
                arguments.get("max_epochs"),
                "max_epochs",
                minimum=1,
                maximum=400,
            )
            accelerator = bounded_text(
                arguments.get("accelerator"),
                "accelerator",
                default="auto",
                maximum=4,
                allowed={"auto", "cpu", "gpu"},
            )
        except ValueError as exc:
            return {"error": str(exc)}

        try:
            adata = _prepare_adata(adata_path, n_top_genes)
        except ValueError as exc:
            return {"error": f"Invalid adata_path: {exc}"}
        if batch_key and batch_key not in adata.obs:
            return {"error": "batch_key was not found in adata.obs."}
        try:
            model = _train_scvi(adata, batch_key, n_latent, max_epochs, accelerator)
            latent = np.asarray(model.get_latent_representation(), dtype=float)
        except Exception:
            return {"error": "scVI integration failed on the provider."}
        if (
            latent.ndim != 2
            or latent.shape[0] != adata.n_obs
            or latent.shape[1] > 128
            or not np.isfinite(latent).all()
        ):
            return {"error": "scVI returned an invalid latent representation."}
        result = {
            "model": "scVI",
            "n_cells": int(latent.shape[0]),
            "n_latent": int(latent.shape[1]),
            "batch_key": batch_key,
        }
        if latent.shape[0] <= _MAX_INLINE_CELLS:
            result["latent_representation"] = latent.tolist()
            result["cell_ids"] = adata.obs_names.astype(str).tolist()
        else:
            result["note"] = (
                f"Per-cell output omitted because n_cells exceeds "
                f"{_MAX_INLINE_CELLS}."
            )
        return result


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
                    "description": "An .h5ad file of raw UMI counts inside the provider-configured data directory.",
                },
                "groupby": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 128,
                    "description": "obs column defining the groups to compare (e.g. 'cell_type').",
                },
                "group1": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 128,
                    "description": "Value in `groupby` for the foreground group.",
                },
                "group2": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 128,
                    "description": "Value in `groupby` for the reference group (optional; default = rest).",
                },
                "batch_key": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 128,
                    "description": "obs column naming the batch/sample (optional).",
                },
                "max_epochs": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 400,
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
        try:
            arguments = require_argument_object(arguments)
        except ValueError as exc:
            return {"error": str(exc)}
        adata_path = arguments.get("adata_path")
        if not adata_path or not arguments.get("groupby") or not arguments.get("group1"):
            return {
                "error": "Missing required parameter(s): adata_path, groupby, group1"
            }
        try:
            groupby = bounded_text(arguments.get("groupby"), "groupby")
            group1 = bounded_text(arguments.get("group1"), "group1")
            group2 = bounded_text(arguments.get("group2"), "group2")
            batch_key = bounded_text(arguments.get("batch_key"), "batch_key")
            max_epochs = bounded_integer(
                arguments.get("max_epochs"),
                "max_epochs",
                minimum=1,
                maximum=400,
            )
        except ValueError as exc:
            return {"error": str(exc)}

        try:
            adata = _prepare_adata(adata_path, n_top_genes=0)
        except ValueError as exc:
            return {"error": f"Invalid adata_path: {exc}"}
        if groupby not in adata.obs:
            return {"error": "groupby was not found in adata.obs."}
        if batch_key and batch_key not in adata.obs:
            return {"error": "batch_key was not found in adata.obs."}
        group_values = set(adata.obs[groupby].astype(str))
        if group1 not in group_values or (group2 is not None and group2 not in group_values):
            return {"error": "The requested comparison group was not found."}
        try:
            model = _train_scvi(adata, batch_key, 10, max_epochs, "auto")
            de = model.differential_expression(
                groupby=groupby, group1=group1, group2=group2
            )
            de = de.reset_index().rename(columns={"index": "gene"})
            n_genes = int(de.shape[0])
            records = json.loads(de.head(_MAX_DE_GENES).to_json(orient="records"))
        except Exception:
            return {"error": "scVI differential expression failed on the provider."}
        return {
            "model": "scVI",
            "groupby": groupby,
            "group1": group1,
            "group2": group2 or "rest",
            "n_genes": n_genes,
            "n_genes_returned": len(records),
            "differential_expression": records,
            "truncated": n_genes > len(records),
        }


if __name__ == "__main__":
    start_mcp_server()
