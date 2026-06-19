"""
CellTypist automated single-cell type annotation — MCP Server.

CellTypist (Domínguez Conde et al., Science 2022; Xu et al., Bioinformatics
2023) is a logistic-regression-based tool for automated cell-type annotation of
single-cell RNA-seq data. It ships a large collection of pre-trained models
(immune, lung, brain, developmental, pan-tissue, ...) and predicts a cell-type
label for every cell, with an optional over-clustering "majority-voting"
refinement that harmonises predictions within transcriptionally similar groups.

This module exposes CellTypist as a ToolUniverse *remote* tool because it
carries a single-cell dependency stack (`celltypist` -> scikit-learn +
scanpy/anndata) and downloads model files on first use. Running it on a
dedicated server keeps the core ToolUniverse install light.

Inputs are referenced by an ``adata_path`` (a server-accessible ``.h5ad``)
rather than inlined, because single-cell matrices are large. CellTypist expects
expression that is log1p-normalised to 10,000 counts per cell, so the module
normalises a copy of the matrix before annotating.

One operation is served:
  * run_celltypist_annotate -> per-cell predicted labels + cell-type counts

References
----------
Domínguez Conde C, Xu C, Jarvis LB, et al. "Cross-tissue immune cell analysis
reveals tissue-specific features in humans." Science 376, eabl5197 (2022).
Xu C, Prete M, Webb S, et al. "Automatic cell-type harmonization and
integration across Human Cell Atlas datasets." Cell 186, 5876-5891 (2023).
"""

from typing import Any, Dict

import celltypist
import scanpy as sc
from celltypist import models

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server


def _prepare_adata(adata_path: str):
    """Load an .h5ad and log1p-normalise to 10,000 counts (CellTypist's input)."""
    adata = sc.read_h5ad(adata_path)
    sc.pp.normalize_total(adata, target_sum=1e4)
    sc.pp.log1p(adata)
    return adata


@register_mcp_tool(
    tool_type_name="run_celltypist_annotate",
    config={
        "description": (
            "Annotate single-cell RNA-seq data with CellTypist: predict a "
            "cell-type label for every cell using a pre-trained logistic-"
            "regression model and return the per-cell labels plus a cell-type "
            "count summary. Optional majority-voting over-clustering harmonises "
            "predictions within transcriptionally similar groups."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "adata_path": {
                    "type": "string",
                    "description": "Server-accessible path or URL to an .h5ad AnnData of single-cell expression (raw or normalized counts).",
                },
                "model": {
                    "type": "string",
                    "description": "CellTypist pre-trained model name (default 'Immune_All_Low.pkl'). Other examples: 'Immune_All_High.pkl', 'Adult_Mouse_Gut.pkl', 'Human_Lung_Atlas.pkl'.",
                },
                "majority_voting": {
                    "type": "boolean",
                    "description": "Refine predictions by over-clustering so cells in the same group share a label (default true).",
                },
            },
            "required": ["adata_path"],
        },
    },
    mcp_config={
        "server_name": "CellTypist MCP Server",
        "host": "127.0.0.1",
        "port": 8014,
        "transport": "http",
    },
)
class CelltypistAnnotateTool:
    """Annotate cells with a pre-trained CellTypist model."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        adata_path = arguments.get("adata_path")
        if not adata_path:
            return {"error": "Missing required parameter: adata_path"}
        model = arguments.get("model") or "Immune_All_Low.pkl"
        majority_voting = arguments.get("majority_voting")
        majority_voting = True if majority_voting is None else bool(majority_voting)

        try:
            adata = _prepare_adata(adata_path)
            models.download_models(model=model)  # fetch the built-in model if absent
            predictions = celltypist.annotate(
                adata, model=model, majority_voting=majority_voting
            )
            labels_df = predictions.predicted_labels
            # majority_voting adds a 'majority_voting' column; otherwise use
            # 'predicted_labels'. Prefer the refined column when present.
            if "majority_voting" in labels_df.columns:
                label_series = labels_df["majority_voting"]
            else:
                label_series = labels_df["predicted_labels"]
            label_series = label_series.astype(str)
            predicted_labels = label_series.tolist()
            cell_ids = labels_df.index.astype(str).tolist()
            label_counts = {
                str(k): int(v) for k, v in label_series.value_counts().items()
            }
            return {
                "model": model,
                "majority_voting": majority_voting,
                "n_cells": len(cell_ids),
                "cell_ids": cell_ids,
                "predicted_labels": predicted_labels,
                "label_counts": label_counts,
            }
        except Exception as exc:  # never raise out of run()
            return {"error": f"CellTypist annotation failed: {exc}"}


if __name__ == "__main__":
    start_mcp_server()
