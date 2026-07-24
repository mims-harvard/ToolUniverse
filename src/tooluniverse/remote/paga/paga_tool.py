"""
PAGA single-cell trajectory / cluster-connectivity — MCP Server.

PAGA (Partition-based Graph Abstraction; Wolf et al., Genome Biology 2019) is a
scanpy-native method that summarizes a single-cell neighborhood graph at the
level of cell clusters. For each pair of clusters it estimates a connectivity
score — the statistical likelihood of inter-cluster connections relative to
random — yielding a coarse-grained "abstracted" graph whose strong edges sketch
the differentiation/trajectory backbone of the data.

This module exposes PAGA as a ToolUniverse *remote* tool because it carries a
scanpy dependency stack (`scanpy` -> anndata + igraph + leidenalg) that the core
ToolUniverse install keeps light. The computation itself is cheap once a
neighbors graph exists; the cluster x cluster connectivity matrix returned is
small and bounded.

Inputs are referenced by an ``adata_path`` (a server-accessible ``.h5ad`` whose
``obs`` already carries the requested ``cluster_key``) rather than inlined,
because single-cell matrices are large.

One operation is served:
  * run_paga_trajectory -> cluster connectivity matrix + trajectory-backbone edges

References
----------
Wolf FA, Hamey FK, Plass M, et al. "PAGA: graph abstraction reconciles
clustering with trajectory inference through a topology preserving map of single
cells." Genome Biology 20, 59 (2019).
"""

from typing import Any, Dict

import numpy as np
import scanpy as sc

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server


def _ensure_neighbors(adata):
    """Build a neighbors graph if one is not already present.

    Log-normalizes raw-looking counts, runs PCA, then computes neighbors. A
    pre-existing ``adata.uns["neighbors"]`` is respected and left untouched.
    """
    if "neighbors" in adata.uns:
        return

    # Log-normalize only if the matrix still looks like raw counts.
    x_max = adata.X.max()
    if hasattr(x_max, "item"):
        x_max = x_max.item()
    looks_raw = float(x_max) > 50.0
    if looks_raw:
        sc.pp.normalize_total(adata, target_sum=1e4)
        sc.pp.log1p(adata)

    n_comps = min(50, max(1, adata.n_vars - 1))
    sc.pp.pca(adata, n_comps=n_comps)
    sc.pp.neighbors(adata)


@register_mcp_tool(
    tool_type_name="run_paga_trajectory",
    config={
        "description": (
            "Run PAGA (Partition-based Graph Abstraction; Wolf et al. 2019) on a "
            "single-cell AnnData to estimate connectivity between cell clusters. "
            "Builds a neighbors graph if one is absent, then computes the "
            "cluster x cluster connectivity matrix and reports the strongest "
            "connected cluster pairs (edges above a threshold) that sketch the "
            "trajectory backbone."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "adata_path": {
                    "type": "string",
                    "description": "Server-accessible path or URL to an .h5ad AnnData whose obs contains `cluster_key`.",
                },
                "cluster_key": {
                    "type": "string",
                    "description": "obs column holding the discrete cluster labels (e.g. 'leiden' or 'cell_type').",
                },
                "threshold": {
                    "type": "number",
                    "description": "Minimum connectivity for an edge to be reported (default 0.1).",
                },
            },
            "required": ["adata_path", "cluster_key"],
        },
    },
    mcp_config={
        "server_name": "PAGA MCP Server",
        "host": "127.0.0.1",
        "port": 8022,
        "transport": "http",
    },
)
class PagaTrajectoryTool:
    """Run PAGA and return the cluster connectivity matrix + backbone edges."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        adata_path = arguments.get("adata_path")
        cluster_key = arguments.get("cluster_key")
        if not adata_path:
            return {"error": "Missing required parameter: adata_path"}
        if not cluster_key:
            return {"error": "Missing required parameter: cluster_key"}
        threshold = arguments.get("threshold")
        threshold = 0.1 if threshold is None else float(threshold)

        try:
            adata = sc.read_h5ad(adata_path)
        except Exception as exc:  # noqa: BLE001
            return {"error": f"Failed to read adata_path '{adata_path}': {exc}"}

        if cluster_key not in adata.obs:
            return {
                "error": (
                    f"cluster_key '{cluster_key}' not found in adata.obs. "
                    f"Available columns: {list(adata.obs.columns)}"
                )
            }

        # PAGA requires a categorical grouping.
        if str(adata.obs[cluster_key].dtype) != "category":
            adata.obs[cluster_key] = adata.obs[cluster_key].astype("category")
        clusters = adata.obs[cluster_key].cat.categories.astype(str).tolist()
        if len(clusters) < 2:
            return {
                "error": (
                    f"cluster_key '{cluster_key}' has only {len(clusters)} category; "
                    "PAGA needs at least 2 clusters."
                )
            }

        try:
            _ensure_neighbors(adata)
            sc.tl.paga(adata, groups=cluster_key)
        except Exception as exc:  # noqa: BLE001
            return {"error": f"PAGA computation failed: {exc}"}

        conn = adata.uns["paga"]["connectivities"]
        # Densify the sparse cluster x cluster matrix (small, bounded).
        dense = conn.toarray() if hasattr(conn, "toarray") else np.asarray(conn)
        dense = np.asarray(dense, dtype=float)

        # Collect upper-triangle edges above threshold (matrix is symmetric).
        edges = []
        n = dense.shape[0]
        for i in range(n):
            for j in range(i + 1, n):
                weight = float(dense[i, j])
                if weight >= threshold:
                    edges.append(
                        {
                            "from": clusters[i],
                            "to": clusters[j],
                            "connectivity": weight,
                        }
                    )
        edges.sort(key=lambda e: e["connectivity"], reverse=True)

        return {
            "clusters": clusters,
            "connectivity_matrix": dense.tolist(),
            "edges": edges,
            "note": (
                f"PAGA on '{cluster_key}': {len(clusters)} clusters, "
                f"{len(edges)} edge(s) with connectivity >= {threshold}. "
                "Strong edges sketch the trajectory backbone."
            ),
        }


if __name__ == "__main__":
    start_mcp_server()
