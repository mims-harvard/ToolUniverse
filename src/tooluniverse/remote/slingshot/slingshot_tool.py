"""
Slingshot trajectory inference — MCP Server.

Slingshot (Street et al., BMC Genomics 2018) infers developmental lineages and
per-cell pseudotime from single-cell data. Given a low-dimensional embedding and
cluster labels, it builds a minimum spanning tree on the cluster centroids to
order them into smooth lineages, fits simultaneous principal curves, and assigns
each cell a pseudotime along every lineage it belongs to. It is a standard
trajectory method, robust for tree-shaped differentiation.

Served as a ToolUniverse *remote* tool because the engine is R/Bioconductor
(`slingshot`). The Python side reads the ``.h5ad`` with scanpy, extracts the
chosen embedding (``obsm``) and cluster labels (``obs``), and hands them to the
bundled R script; the script runs ``slingshot`` and returns the lineage
structure and pseudotime as JSON.

One operation:
  * run_slingshot_trajectory -> lineages (ordered cluster sequences) + pseudotime

Reference
---------
Street K, Risso D, Fletcher RB, et al. "Slingshot: cell lineage and pseudotime
inference for single-cell transcriptomics." BMC Genomics 19, 477 (2018).
"""

import json
import os
import subprocess
import tempfile
from typing import Any, Dict

import numpy as np
import scanpy as sc

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server

_R_SCRIPT = os.path.join(os.path.dirname(__file__), "slingshot_trajectory.R")
_RSCRIPT = os.environ.get("RSCRIPT_BIN", "Rscript")
_TIMEOUT = 1800
_MAX_PSEUDOTIME_CELLS = 50000


def _run_rscript(work: str) -> Dict[str, Any]:
    """Run the bundled Slingshot R script over a prepared work dir; return parsed JSON."""
    if not os.path.exists(_R_SCRIPT):
        return {"error": f"Slingshot R script not found at {_R_SCRIPT}."}
    try:
        proc = subprocess.run(
            [_RSCRIPT, _R_SCRIPT, work],
            capture_output=True,
            text=True,
            timeout=_TIMEOUT,
        )
    except FileNotFoundError:
        return {
            "error": f"Rscript not found ('{_RSCRIPT}'); install R + the slingshot package."
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Slingshot timed out after {_TIMEOUT}s."}
    out_path = os.path.join(work, "output.json")
    if proc.returncode != 0 or not os.path.exists(out_path):
        return {
            "error": f"Slingshot (R) failed: {proc.stderr[-600:] or proc.stdout[-600:]}"
        }
    with open(out_path) as fh:
        return json.load(fh)


@register_mcp_tool(
    tool_type_name="run_slingshot_trajectory",
    config={
        "description": (
            "Infer single-cell lineages and pseudotime with Slingshot (Street "
            "2018): from a low-dimensional embedding + cluster labels, order "
            "clusters into smooth lineages (minimum spanning tree + principal "
            "curves) and assign each cell a pseudotime along every lineage. "
            "Returns the lineage structure (ordered cluster sequences) and "
            "per-cell pseudotime. Optionally anchor with a known start and/or "
            "terminal clusters."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "adata_path": {
                    "type": "string",
                    "description": "Server-accessible path to an .h5ad AnnData with a reduced embedding in obsm and cluster labels in obs.",
                },
                "embedding_key": {
                    "type": "string",
                    "description": "obsm key of the embedding to build the trajectory on (default 'X_pca'; e.g. 'X_umap').",
                },
                "cluster_key": {
                    "type": "string",
                    "description": "obs column with cluster labels whose centroids are ordered into lineages.",
                },
                "start_cluster": {
                    "type": "string",
                    "description": "Known root cluster to start every lineage from (optional but recommended for directionality).",
                },
                "end_clusters": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Known terminal cluster(s) to force as lineage endpoints (optional).",
                },
                "n_dims": {
                    "type": "integer",
                    "description": "Use only the first n_dims columns of the embedding (default: all; for X_pca, 10-20 is typical).",
                },
            },
            "required": ["adata_path", "cluster_key"],
        },
    },
    mcp_config={
        "server_name": "Slingshot Trajectory MCP Server",
        "host": "127.0.0.1",
        "port": 8030,
        "transport": "http",
    },
)
class SlingshotTrajectoryTool:
    """Infer lineages and pseudotime from an embedding + clusters with Slingshot."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        adata_path = arguments.get("adata_path")
        cluster_key = arguments.get("cluster_key")
        if not adata_path:
            return {"error": "Missing required parameter: adata_path"}
        if not cluster_key:
            return {"error": "Missing required parameter: cluster_key"}
        embedding_key = arguments.get("embedding_key") or "X_pca"

        adata = sc.read_h5ad(adata_path)
        if embedding_key not in adata.obsm:
            return {
                "error": f"embedding_key '{embedding_key}' not in adata.obsm ({list(adata.obsm)})."
            }
        if cluster_key not in adata.obs:
            return {"error": f"cluster_key '{cluster_key}' not in adata.obs."}

        emb = np.asarray(adata.obsm[embedding_key], dtype=float)
        n_dims = arguments.get("n_dims")
        if n_dims:
            emb = emb[:, : int(n_dims)]
        clusters = adata.obs[cluster_key].astype(str).to_numpy()

        with tempfile.TemporaryDirectory() as work:
            np.savetxt(os.path.join(work, "embedding.csv"), emb, delimiter=",")
            with open(os.path.join(work, "clusters.txt"), "w") as fh:
                fh.write("\n".join(clusters))
            config = {
                "start_cluster": arguments.get("start_cluster") or "",
                "end_clusters": arguments.get("end_clusters") or [],
                "max_pseudotime_cells": _MAX_PSEUDOTIME_CELLS,
            }
            with open(os.path.join(work, "config.json"), "w") as fh:
                json.dump(config, fh)
            res = _run_rscript(work)

        if "error" in res:
            return res
        res["model"] = "Slingshot"
        res["embedding_key"] = embedding_key
        res["n_cells"] = int(emb.shape[0])
        if "pseudotime" in res:
            res["cell_ids"] = adata.obs_names.astype(str).tolist()
        return res


if __name__ == "__main__":
    start_mcp_server()
