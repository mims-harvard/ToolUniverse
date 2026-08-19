"""
scANVI semi-supervised single-cell annotation / reference label transfer — MCP Server.

scANVI (single-cell ANnotation using Variational Inference; Xu et al.,
Molecular Systems Biology 2021; scvi-tools platform: Gayoso et al., Nature
Biotechnology 2022) is a semi-supervised extension of scVI. It learns a
batch-corrected latent representation from raw UMI counts while jointly modeling
cell-type labels, so a model trained on a *partially* labeled dataset can
transfer labels to the unlabeled cells.

This module exposes scANVI as a ToolUniverse *remote* tool because it carries a
heavy deep-learning dependency stack (`scvi-tools` -> PyTorch + Lightning +
Pyro + scanpy/anndata). Running it on a dedicated server keeps the core
ToolUniverse install light; the model trains on CPU for small datasets and on
GPU for large ones.

Inputs are referenced by an ``adata_path`` (a server-accessible ``.h5ad`` of
raw counts) rather than inlined, because single-cell matrices are large. The
AnnData must carry a ``labels_key`` obs column in which *some* cells hold their
known cell type and the unlabeled cells hold the ``unlabeled_category`` sentinel
(default ``"Unknown"``).

Standard flow:
  * scvi.model.SCVI.setup_anndata + SCVI.train      -> unsupervised pretraining
  * SCANVI.from_scvi_model + SCANVI.train           -> semi-supervised refinement
  * SCANVI.predict()                                -> predicted label per cell

One operation is served:
  * run_scanvi_annotate -> predicted labels for the previously-unlabeled cells

References
----------
Xu C, Lopez R, Mehlman E, Regier J, Jordan MI, Yosef N. "Probabilistic harmonization
and annotation of single-cell transcriptomics data with deep generative models."
Molecular Systems Biology 17, e9620 (2021).
Gayoso A, Lopez R, Xing G, et al. "A Python library for probabilistic analysis
of single-cell omics data." Nature Biotechnology 40, 163-166 (2022).
"""

from typing import Any, Dict

import scanpy as sc
import scvi

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server
from tooluniverse.remote_argument_validation import (
    bounded_integer,
    bounded_text,
    require_argument_object,
)
from tooluniverse.remote_data_path import load_remote_h5ad

# Above this cell count, per-cell arrays are omitted from the response to keep
# the payload bounded; only the label-count summary is returned.
_CELL_ARRAY_LIMIT = 5000


@register_mcp_tool(
    tool_type_name="run_scanvi_annotate",
    config={
        "description": (
            "Transfer cell-type labels to unlabeled single cells with scANVI "
            "(semi-supervised single-cell annotation; Xu 2021 / scvi-tools, "
            "Gayoso 2022). Pretrains scVI on a raw-count matrix, refines it "
            "semi-supervised on the known labels, then predicts a label for "
            "every cell. Input is a server-accessible .h5ad of RAW UMI counts "
            "whose `labels_key` obs column holds known cell types for some "
            "cells and the `unlabeled_category` sentinel (default 'Unknown') "
            "for the rest."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "adata_path": {
                    "type": "string",
                    "description": "An .h5ad file of raw UMI counts inside the provider-configured data directory.",
                },
                "labels_key": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 128,
                    "description": "obs column holding known cell-type labels for some cells and the unlabeled_category sentinel for the cells to annotate.",
                },
                "unlabeled_category": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 128,
                    "description": "Value in labels_key marking unlabeled cells (default 'Unknown').",
                },
                "scvi_epochs": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 400,
                    "description": "Unsupervised scVI pretraining epochs (default 100).",
                },
                "scanvi_epochs": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 200,
                    "description": "Semi-supervised scANVI refinement epochs (default 20).",
                },
            },
            "required": ["adata_path", "labels_key"],
        },
    },
    mcp_config={
        "server_name": "scANVI MCP Server",
        "host": "127.0.0.1",
        "port": 8027,
        "transport": "http",
    },
)
class ScanviAnnotateTool:
    """Train scANVI on a partially-labeled count matrix and transfer labels."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            arguments = require_argument_object(arguments)
        except ValueError as exc:
            return {"error": str(exc)}
        adata_path = arguments.get("adata_path")
        labels_key = arguments.get("labels_key")
        if not adata_path:
            return {"error": "Missing required parameter: adata_path"}
        if not labels_key:
            return {"error": "Missing required parameter: labels_key"}

        try:
            labels_key = bounded_text(labels_key, "labels_key")
            unlabeled_category = bounded_text(
                arguments.get("unlabeled_category"),
                "unlabeled_category",
                default="Unknown",
            )
            scvi_epochs = bounded_integer(
                arguments.get("scvi_epochs"),
                "scvi_epochs",
                default=100,
                minimum=1,
                maximum=400,
            )
            scanvi_epochs = bounded_integer(
                arguments.get("scanvi_epochs"),
                "scanvi_epochs",
                default=20,
                minimum=1,
                maximum=200,
            )
        except ValueError as exc:
            return {"error": str(exc)}

        try:
            adata = load_remote_h5ad(adata_path, sc.read_h5ad)
        except Exception as exc:  # noqa: BLE001
            return {"error": f"Invalid adata_path: {exc}"}

        if labels_key not in adata.obs:
            return {"error": "labels_key was not found in adata.obs."}

        try:
            # Preserve raw counts in a 'counts' layer before any normalization.
            if "counts" not in adata.layers:
                adata.layers["counts"] = adata.X.copy()

            label_values = adata.obs[labels_key].astype(str)
            unlabeled_mask = (label_values == unlabeled_category).to_numpy()
            n_cells = int(adata.n_obs)
            n_unlabeled = int(unlabeled_mask.sum())

            if n_unlabeled == 0:
                return {"error": "No cells use the requested unlabeled_category."}
            if n_unlabeled == n_cells:
                return {
                    "error": (
                        f"All cells are unlabeled (labels_key '{labels_key}' "
                        f"== '{unlabeled_category}'); scANVI needs some labeled "
                        "cells to learn from."
                    )
                }

            # Unsupervised scVI pretraining on raw counts.
            scvi.model.SCVI.setup_anndata(adata, layer="counts")
            scvi_model = scvi.model.SCVI(adata)
            scvi_model.train(max_epochs=scvi_epochs)

            # Semi-supervised scANVI refinement initialised from the scVI model.
            scanvi_model = scvi.model.SCANVI.from_scvi_model(
                scvi_model,
                unlabeled_category=unlabeled_category,
                labels_key=labels_key,
            )
            scanvi_model.train(max_epochs=scanvi_epochs)

            preds = scanvi_model.predict()
        except Exception as exc:  # noqa: BLE001
            return {"error": "scANVI annotation failed on the provider."}

        preds = [str(p) for p in preds]
        if len(preds) != n_cells:
            return {"error": "scANVI returned an invalid number of predictions."}
        if any(not label or len(label) > 128 for label in preds):
            return {"error": "scANVI returned an invalid prediction label."}
        cell_ids = adata.obs_names.astype(str).tolist()

        # Label counts over the predictions for the previously-unlabeled cells.
        label_counts: Dict[str, int] = {}
        for keep, label in zip(unlabeled_mask, preds):
            if keep:
                label_counts[label] = label_counts.get(label, 0) + 1
        if len(label_counts) > 256:
            return {"error": "scANVI returned too many distinct prediction labels."}

        result: Dict[str, Any] = {
            "model": "scANVI",
            "labels_key": labels_key,
            "unlabeled_category": unlabeled_category,
            "n_cells": n_cells,
            "n_unlabeled": n_unlabeled,
            "label_counts": label_counts,
        }

        # Bound the per-cell arrays: predictions for the previously-unlabeled
        # cells plus their ids, omitted entirely for very large datasets.
        if n_cells <= _CELL_ARRAY_LIMIT:
            result["predicted_labels"] = [
                label for keep, label in zip(unlabeled_mask, preds) if keep
            ]
            result["cell_ids"] = [
                cid for keep, cid in zip(unlabeled_mask, cell_ids) if keep
            ]
        else:
            result["note"] = (
                f"n_cells ({n_cells}) exceeds {_CELL_ARRAY_LIMIT}; per-cell "
                "predicted_labels/cell_ids arrays omitted — see label_counts."
            )

        return result


if __name__ == "__main__":
    start_mcp_server()
