"""
Harmony single-cell batch integration — MCP Server.

Harmony (Korsunsky et al., Nature Methods 2019) is the default baseline for
correcting batch/sample effects in single-cell data. It operates on a
low-dimensional PCA embedding, iteratively clustering cells in a
batch-aware soft k-means and applying linear correction so that cells from
different batches mix while biological structure is preserved. The corrected
embedding is the standard input to neighbor graphs / clustering / UMAP.

This module exposes Harmony as a ToolUniverse *remote* tool because it carries
a single-cell analysis dependency stack (`harmonypy` + `scanpy`/`anndata`).
Running it on a dedicated server keeps the core ToolUniverse install light.
Harmony is fast and CPU-friendly even for large datasets.

Inputs are referenced by an ``adata_path`` (a server-accessible ``.h5ad``)
rather than inlined, because single-cell matrices are large. If the AnnData
already carries a PCA embedding in ``obsm['X_pca']`` it is used directly;
otherwise PCA is computed (log-normalizing first if the matrix looks like raw
counts).

One operation is served:
  * run_harmony_integrate -> batch-corrected PCA embedding (X_pca_harmony)

References
----------
Korsunsky I, Millard N, Fan J, et al. "Fast, sensitive and accurate
integration of single-cell data with Harmony." Nature Methods 16,
1289-1296 (2019).
"""

from typing import Any, Dict

import numpy as np
import scanpy as sc
import harmonypy

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server

# Cap on cells for which the full corrected embedding is returned inline;
# larger datasets get a note instead to keep responses bounded.
_MAX_EMBEDDING_CELLS = 2000


def _looks_like_raw_counts(adata) -> bool:
    """Heuristic: integer-valued, non-negative X => raw UMI counts."""
    try:
        X = adata.X
        sample = X[:100] if X.shape[0] > 100 else X
        arr = sample.toarray() if hasattr(sample, "toarray") else np.asarray(sample)
        if arr.size == 0:
            return False
        if arr.min() < 0:
            return False
        return bool(np.allclose(arr, np.round(arr)))
    except Exception:
        return False


@register_mcp_tool(
    tool_type_name="run_harmony_integrate",
    config={
        "description": (
            "Integrate single-cell data across batches/samples with Harmony "
            "(Korsunsky et al., Nature Methods 2019) — the default batch-"
            "correction baseline. Computes (or reuses) a PCA embedding and "
            "returns the batch-corrected PCA embedding (X_pca_harmony), the "
            "standard input to neighbor graphs / clustering / UMAP. Input is a "
            "server-accessible .h5ad AnnData."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "adata_path": {
                    "type": "string",
                    "description": "Server-accessible path or URL to an .h5ad AnnData.",
                },
                "batch_key": {
                    "type": "string",
                    "description": "obs column naming the batch/sample to integrate over.",
                },
                "n_pcs": {
                    "type": "integer",
                    "description": "Number of principal components to compute/use for Harmony (default 30).",
                },
            },
            "required": ["adata_path", "batch_key"],
        },
    },
    mcp_config={
        "server_name": "Harmony MCP Server",
        "host": "127.0.0.1",
        "port": 8026,
        "transport": "http",
    },
)
class HarmonyIntegrateTool:
    """Run Harmony and return the batch-corrected PCA embedding."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        adata_path = arguments.get("adata_path")
        batch_key = arguments.get("batch_key")
        if not adata_path:
            return {"error": "Missing required parameter: adata_path"}
        if not batch_key:
            return {"error": "Missing required parameter: batch_key"}
        n_pcs = arguments.get("n_pcs")
        n_pcs = 30 if n_pcs is None else int(n_pcs)
        if n_pcs < 1:
            return {"error": "n_pcs must be a positive integer."}

        try:
            adata = sc.read_h5ad(adata_path)
        except Exception as exc:
            return {"error": f"Failed to read AnnData from {adata_path}: {exc}"}

        if batch_key not in adata.obs.columns:
            return {
                "error": (
                    f"batch_key '{batch_key}' not found in adata.obs. "
                    f"Available columns: {list(adata.obs.columns)}"
                )
            }

        try:
            if "X_pca" not in adata.obsm:
                # Log-normalize first if the matrix looks like raw counts.
                if _looks_like_raw_counts(adata):
                    sc.pp.normalize_total(adata, target_sum=1e4)
                    sc.pp.log1p(adata)
                # Never request more components than the data can provide.
                n_comps = min(n_pcs, adata.n_vars - 1, adata.n_obs - 1)
                if n_comps < 1:
                    return {"error": "Too few cells/genes to compute a PCA embedding."}
                sc.pp.pca(adata, n_comps=n_comps)
        except Exception as exc:
            return {"error": f"PCA computation failed: {exc}"}

        try:
            # Call harmonypy directly (not scanpy.external.pp.harmony_integrate):
            # harmonypy >= 2.0 returns Z_corr as (n_cells, n_pcs), but the scanpy
            # wrapper transposes assuming the old (n_pcs, n_cells) layout, which
            # mis-shapes X_pca_harmony. Orient by whichever axis matches n_obs.
            ho = harmonypy.run_harmony(adata.obsm["X_pca"], adata.obs, [batch_key])
            z = np.asarray(ho.Z_corr)
            if z.shape[0] != adata.n_obs:
                z = z.T
            adata.obsm["X_pca_harmony"] = z
        except Exception as exc:
            return {"error": f"Harmony integration failed: {exc}"}

        try:
            corrected = adata.obsm["X_pca_harmony"]
            n_cells = int(corrected.shape[0])
            # Downstream PC count is whatever X_pca actually produced — never
            # the requested n_pcs, which may exceed the available dimensions.
            actual_n_pcs = int(corrected.shape[1])
            batches = adata.obs[batch_key].astype(str).unique().tolist()

            result: Dict[str, Any] = {
                "n_cells": n_cells,
                "n_pcs": actual_n_pcs,
                "batch_key": batch_key,
                "batches": batches,
            }
            if n_cells <= _MAX_EMBEDDING_CELLS:
                result["corrected_embedding"] = corrected.tolist()
            else:
                result["note"] = (
                    f"corrected_embedding omitted: {n_cells} cells exceeds the "
                    f"{_MAX_EMBEDDING_CELLS}-cell inline cap. The full "
                    f"X_pca_harmony embedding was written to the AnnData on the "
                    f"server."
                )
            return result
        except Exception as exc:
            return {"error": f"Failed to assemble Harmony result: {exc}"}


if __name__ == "__main__":
    start_mcp_server()
