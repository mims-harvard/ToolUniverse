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

from typing import Any, Dict

import scanpy as sc

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server


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
                    "description": "Server-accessible path or URL to an .h5ad AnnData of RAW counts.",
                },
                "expected_doublet_rate": {
                    "type": "number",
                    "description": "Expected fraction of transcriptomes that are doublets (default 0.06; scale ~0.008 per 1000 cells loaded for 10x).",
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
        adata_path = arguments.get("adata_path")
        if not adata_path:
            return {"error": "Missing required parameter: adata_path"}
        expected_rate = arguments.get("expected_doublet_rate")
        expected_rate = 0.06 if expected_rate is None else float(expected_rate)

        try:
            adata = sc.read_h5ad(adata_path)
        except Exception as exc:
            return {"error": f"Failed to read AnnData from {adata_path}: {exc}"}

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
            except Exception as exc:
                return {"error": f"Scrublet doublet detection failed: {exc}"}

        n_doublets = int(predicted.sum())
        n_cells = int(predicted.shape[0])
        doublet_rate = float(n_doublets / n_cells) if n_cells else 0.0
        return {
            "cell_ids": adata.obs_names.astype(str).tolist(),
            "doublet_score": scores.tolist(),
            "predicted_doublet": predicted.tolist(),
            "n_doublets": n_doublets,
            "doublet_rate": doublet_rate,
        }


if __name__ == "__main__":
    start_mcp_server()
