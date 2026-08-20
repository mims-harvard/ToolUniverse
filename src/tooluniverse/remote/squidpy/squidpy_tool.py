"""
Squidpy spatial neighborhood-enrichment analysis — MCP Server.

Squidpy (Palla et al., Nature Methods 2022) is a toolkit for the analysis and
visualization of spatial molecular data (spatial transcriptomics, imaging-based
single cell). It builds on scanpy/anndata and adds a spatial graph layer plus a
suite of neighborhood statistics.

This module exposes Squidpy's *neighborhood enrichment* test as a ToolUniverse
*remote* tool because it carries a heavy spatial-omics dependency stack
(``squidpy`` -> scanpy/anndata + networkx + scikit-image + numba). Running it on
a dedicated server keeps the core ToolUniverse install light.

The neighborhood-enrichment analysis builds a spatial neighbors graph from the
cell coordinates in ``adata.obsm["spatial"]`` and then, by permutation, tests
which pairs of cluster categories (e.g. cell types) are co-localized
(enriched, positive z-score) or segregated (depleted, negative z-score) more
than expected by chance. The result is a square z-score matrix over the
categories of ``cluster_key``.

Inputs are referenced by an ``adata_path`` (a server-accessible ``.h5ad`` with
``adata.obsm["spatial"]`` coordinates and the ``cluster_key`` column in
``adata.obs``) rather than inlined, because spatial matrices are large.

One operation is served:
  * run_squidpy_nhood_enrichment -> category x category neighborhood-enrichment
                                    z-score matrix

References
----------
Palla G, Spitzer H, Klein M, et al. "Squidpy: a scalable framework for spatial
omics analysis." Nature Methods 19, 171-178 (2022).
"""

from typing import Any, Dict

import scanpy as sc
import squidpy as sq

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server
from tooluniverse.remote_argument_validation import (
    bounded_integer,
    bounded_text,
    require_argument_object,
)
from tooluniverse.remote_data_path import load_remote_h5ad


_MAX_CATEGORIES = 64


@register_mcp_tool(
    tool_type_name="run_squidpy_nhood_enrichment",
    config={
        "description": (
            "Run Squidpy neighborhood enrichment on spatial single-cell data. "
            "Builds a spatial neighbors graph from cell coordinates in "
            "adata.obsm['spatial'], then permutation-tests which pairs of "
            "cluster categories (e.g. cell types) are co-localized (enriched, "
            "positive z-score) or segregated (depleted, negative z-score). "
            "Returns the category x category z-score matrix. Input is a "
            "server-accessible spatial .h5ad."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "adata_path": {
                    "type": "string",
                    "description": "A spatial .h5ad file inside the provider-configured data directory with adata.obsm['spatial'] coordinates and `cluster_key` in adata.obs.",
                },
                "cluster_key": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 128,
                    "description": "obs column with the categorical cluster/cell-type labels to test for co-localization (e.g. 'cell_type').",
                },
                "n_neighs": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Number of nearest spatial neighbors per cell when building the graph (default 6).",
                },
            },
            "required": ["adata_path", "cluster_key"],
        },
    },
    mcp_config={
        "server_name": "Squidpy MCP Server",
        "host": "127.0.0.1",
        "port": 8016,
        "transport": "http",
    },
)
class SquidpyNhoodEnrichmentTool:
    """Build a spatial graph and run Squidpy neighborhood enrichment."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            arguments = require_argument_object(arguments)
        except ValueError as exc:
            return {"error": str(exc)}
        adata_path = arguments.get("adata_path")
        cluster_key = arguments.get("cluster_key")
        if not (adata_path and cluster_key):
            return {"error": "Missing required parameter(s): adata_path, cluster_key"}
        try:
            cluster_key = bounded_text(cluster_key, "cluster_key")
            n_neighs = bounded_integer(
                arguments.get("n_neighs"),
                "n_neighs",
                default=6,
                minimum=1,
                maximum=100,
            )
        except ValueError as exc:
            return {"error": str(exc)}

        try:
            adata = load_remote_h5ad(adata_path, sc.read_h5ad)
        except Exception as exc:
            return {"error": f"Invalid adata_path: {exc}"}

        if "spatial" not in adata.obsm:
            return {"error": "adata.obsm['spatial'] coordinates not found."}
        spatial = adata.obsm["spatial"]
        if (
            getattr(spatial, "ndim", None) != 2
            or spatial.shape[0] != adata.n_obs
            or spatial.shape[1] < 2
        ):
            return {"error": "adata.obsm['spatial'] has an invalid shape."}
        if n_neighs >= adata.n_obs:
            return {"error": "n_neighs must be smaller than the number of cells."}
        if cluster_key not in adata.obs:
            return {"error": "cluster_key was not found in adata.obs."}

        try:
            # Squidpy permutation tests require a categorical cluster key.
            if str(adata.obs[cluster_key].dtype) != "category":
                adata.obs[cluster_key] = adata.obs[cluster_key].astype("category")
            categories = adata.obs[cluster_key].cat.categories.astype(str).tolist()
            if len(categories) < 2 or len(categories) > _MAX_CATEGORIES:
                return {
                    "error": (
                        f"cluster_key must contain between 2 and "
                        f"{_MAX_CATEGORIES} categories."
                    )
                }
            if any(not category or len(category) > 128 for category in categories):
                return {"error": "cluster_key contains an invalid category label."}
            sq.gr.spatial_neighbors(adata, coord_type="generic", n_neighs=n_neighs)
            # seed for reproducibility; n_jobs=1 avoids multiprocessing-spawn
            # issues when the server runs outside an `if __name__ == '__main__'`.
            sq.gr.nhood_enrichment(adata, cluster_key=cluster_key, seed=0, n_jobs=1)
        except Exception:
            return {"error": "Squidpy neighborhood enrichment failed on the provider."}

        result = adata.uns.get(f"{cluster_key}_nhood_enrichment")
        if not result or "zscore" not in result:
            return {"error": "Neighborhood-enrichment z-score matrix not produced."}

        zscore = result["zscore"]
        if (
            getattr(zscore, "shape", None) != (len(categories), len(categories))
            or not bool((zscore == zscore).all())
        ):
            return {"error": "Neighborhood enrichment returned an invalid matrix."}
        return {
            "cluster_key": cluster_key,
            "n_cells": int(adata.n_obs),
            "n_neighs": n_neighs,
            "categories": categories,
            "zscore_matrix": zscore.tolist(),
            "note": (
                "Symmetric category x category z-score matrix from Squidpy "
                "permutation test; positive = co-localized, negative = "
                "segregated. Row/column order matches `categories`."
            ),
        }


if __name__ == "__main__":
    start_mcp_server()
