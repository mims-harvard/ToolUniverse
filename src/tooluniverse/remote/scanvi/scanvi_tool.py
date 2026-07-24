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
                    "description": "Server-accessible path or URL to an .h5ad AnnData of RAW UMI counts.",
                },
                "labels_key": {
                    "type": "string",
                    "description": "obs column holding known cell-type labels for some cells and the unlabeled_category sentinel for the cells to annotate.",
                },
                "unlabeled_category": {
                    "type": "string",
                    "description": "Value in labels_key marking unlabeled cells (default 'Unknown').",
                },
                "scvi_epochs": {
                    "type": "integer",
                    "description": "Unsupervised scVI pretraining epochs (default 100).",
                },
                "scanvi_epochs": {
                    "type": "integer",
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
        adata_path = arguments.get("adata_path")
        labels_key = arguments.get("labels_key")
        if not adata_path:
            return {"error": "Missing required parameter: adata_path"}
        if not labels_key:
            return {"error": "Missing required parameter: labels_key"}

        unlabeled_category = arguments.get("unlabeled_category") or "Unknown"
        scvi_epochs = int(arguments.get("scvi_epochs") or 100)
        scanvi_epochs = int(arguments.get("scanvi_epochs") or 20)

        try:
            adata = sc.read_h5ad(adata_path)
        except Exception as exc:  # noqa: BLE001
            return {"error": f"Failed to read AnnData from '{adata_path}': {exc}"}

        if labels_key not in adata.obs:
            return {
                "error": (
                    f"labels_key '{labels_key}' not found in adata.obs "
                    f"(available: {list(adata.obs.columns)})."
                )
            }

        try:
            # Preserve raw counts in a 'counts' layer before any normalization.
            if "counts" not in adata.layers:
                adata.layers["counts"] = adata.X.copy()

            label_values = adata.obs[labels_key].astype(str)
            unlabeled_mask = (label_values == unlabeled_category).to_numpy()
            n_cells = int(adata.n_obs)
            n_unlabeled = int(unlabeled_mask.sum())

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
            return {"error": f"scANVI annotation failed: {exc}"}

        preds = [str(p) for p in preds]
        cell_ids = adata.obs_names.astype(str).tolist()

        # Label counts over the predictions for the previously-unlabeled cells.
        label_counts: Dict[str, int] = {}
        for keep, label in zip(unlabeled_mask, preds):
            if keep:
                label_counts[label] = label_counts.get(label, 0) + 1

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
