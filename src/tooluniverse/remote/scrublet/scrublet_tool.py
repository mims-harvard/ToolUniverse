"""
Scrublet single-cell doublet detection — MCP Server.

Scrublet (Single-Cell Remover of Doublets; Wolock, Lopez & Klein,
Cell Systems 2019) flags technical doublets — droplets that captured two cells
and were sequenced as one barcode — in single-cell RNA-seq data. It simulates
synthetic doublets from the observed transcriptomes, embeds real and simulated
cells together, and scores each real cell by its local density of simulated
doublets.

This module exposes Scrublet as a ToolUniverse *remote* tool because it carries
a single-cell analysis dependency stack (`scanpy`/`anndata` + scikit-image for
the KNN/UMAP machinery). Running it on a dedicated server keeps the core
ToolUniverse install light.

Inputs are referenced by an ``adata_path`` (a server-accessible ``.h5ad`` of
RAW counts) rather than inlined, because single-cell matrices are large.
Scrublet must operate on raw counts, not normalized/log-transformed data.

One operation is served:
  * run_scrublet_doublets -> per-cell doublet scores + boolean predictions

References
----------
Wolock SL, Lopez R, Klein AM. "Scrublet: Computational Identification of Cell
Doublets in Single-Cell Transcriptomic Data." Cell Systems 8, 281-291 (2019).
"""

import math
from typing import Any, Dict

import scanpy as sc

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server
from tooluniverse.remote_data_path import load_remote_h5ad


_MAX_INLINE_CELLS = 10_000


@register_mcp_tool(
    tool_type_name="run_scrublet_doublets",
    config={
        "description": (
            "Detect technical doublets in a single-cell RNA-seq count matrix "
            "with Scrublet (Wolock et al., Cell Systems 2019). Returns a "
            "per-cell doublet score and a boolean predicted-doublet call so "
            "doublets can be filtered before downstream clustering/annotation. "
            "Input is a server-accessible .h5ad of RAW counts."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "adata_path": {
                    "type": "string",
                    "description": "An .h5ad file inside the provider's TOOLUNIVERSE_REMOTE_DATA_ROOT directory, containing RAW counts.",
                },
                "expected_doublet_rate": {
                    "type": "number",
                    "description": "Expected fraction of transcriptomes that are doublets (default 0.06; scale ~0.008 per 1000 cells loaded for 10x).",
                    "default": 0.06,
                    "exclusiveMinimum": 0,
                    "exclusiveMaximum": 1,
                },
            },
            "required": ["adata_path"],
        },
    },
    mcp_config={
        "server_name": "Scrublet MCP Server",
        "host": "127.0.0.1",
        "port": 8015,
        "transport": "http",
    },
)
class ScrubletDoubletTool:
    """Run Scrublet and return per-cell doublet scores and boolean predictions."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            return {"error": "Arguments must be an object."}
        adata_path = arguments.get("adata_path")
        if not adata_path:
            return {"error": "Missing required parameter: adata_path"}
        expected_rate = arguments.get("expected_doublet_rate")
        if expected_rate is None:
            expected_rate = 0.06
        if isinstance(expected_rate, bool) or not isinstance(
            expected_rate, (int, float)
        ):
            return {"error": "expected_doublet_rate must be a number between 0 and 1"}
        if not math.isfinite(expected_rate) or not 0 < expected_rate < 1:
            return {"error": "expected_doublet_rate must be a number between 0 and 1"}

        try:
            adata = load_remote_h5ad(adata_path, sc.read_h5ad)
        except ValueError as exc:
            if "could not be read" in str(exc):
                return {"error": "Failed to read the provider .h5ad file."}
            return {"error": f"Invalid adata_path: {exc}"}

        try:
            sc.pp.scrublet(adata, expected_doublet_rate=expected_rate)
            scores = adata.obs["doublet_score"].to_numpy().astype(float)
            predicted = adata.obs["predicted_doublet"].to_numpy().astype(bool)
        except Exception:
            # Fallback to the standalone scrublet package if the scanpy-native
            # call is unavailable or fails (e.g. older scanpy without sc.pp.scrublet).
            try:
                import scrublet

                scrub = scrublet.Scrublet(adata.X, expected_doublet_rate=expected_rate)
                scores, predicted = scrub.scrub_doublets()
                scores = scores.astype(float)
                if predicted is None:
                    return {
                        "error": (
                            "Scrublet could not automatically set a threshold; "
                            "no predicted_doublet calls available for this dataset."
                        )
                    }
                predicted = predicted.astype(bool)
            except Exception:
                return {"error": "Scrublet doublet detection failed on the provider."}

        n_doublets = int(predicted.sum())
        n_cells = int(predicted.shape[0])
        score_values = scores.tolist()
        if scores.shape[0] != n_cells or any(
            not math.isfinite(float(score)) for score in score_values
        ):
            return {"error": "Scrublet returned invalid scores on the provider."}
        doublet_rate = float(n_doublets / n_cells) if n_cells else 0.0
        result = {
            "n_doublets": n_doublets,
            "n_cells": n_cells,
            "doublet_rate": doublet_rate,
        }
        if n_cells <= _MAX_INLINE_CELLS:
            result.update(
                {
                    "cell_ids": adata.obs_names.astype(str).tolist(),
                    "doublet_score": score_values,
                    "predicted_doublet": predicted.tolist(),
                }
            )
        else:
            result["note"] = (
                f"Per-cell results omitted because {n_cells} cells exceeds the "
                f"{_MAX_INLINE_CELLS}-cell public output limit."
            )
        return result


if __name__ == "__main__":
    start_mcp_server()
