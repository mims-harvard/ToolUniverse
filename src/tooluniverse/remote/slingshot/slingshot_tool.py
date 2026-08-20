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
import math
import os
import subprocess
import tempfile
from typing import Any, Dict

import numpy as np
import scanpy as sc

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server
from tooluniverse.remote_argument_validation import (
    bounded_integer,
    bounded_text,
    require_argument_object,
)
from tooluniverse.remote_data_path import load_remote_h5ad

_R_SCRIPT = os.path.join(os.path.dirname(__file__), "slingshot_trajectory.R")
_RSCRIPT = os.environ.get("RSCRIPT_BIN", "Rscript")
_TIMEOUT = 1800
_MAX_PSEUDOTIME_CELLS = 5000
_MAX_CLUSTERS = 64
_MAX_OUTPUT_BYTES = 25_000_000


def _run_rscript(work: str) -> Dict[str, Any]:
    """Run the bundled Slingshot R script over a prepared work dir; return parsed JSON."""
    if not os.path.exists(_R_SCRIPT):
        return {"error": "The provider's bundled Slingshot script is unavailable."}
    try:
        proc = subprocess.run(
            [_RSCRIPT, _R_SCRIPT, work],
            capture_output=True,
            text=True,
            timeout=_TIMEOUT,
        )
    except FileNotFoundError:
        return {"error": "The provider's Rscript executable is unavailable."}
    except subprocess.TimeoutExpired:
        return {"error": f"Slingshot timed out after {_TIMEOUT}s."}
    except OSError:
        return {"error": "The provider could not start Slingshot."}
    out_path = os.path.join(work, "output.json")
    if proc.returncode != 0 or not os.path.exists(out_path):
        return {"error": f"Slingshot failed on the provider (returncode {proc.returncode})."}
    if os.path.getsize(out_path) > _MAX_OUTPUT_BYTES:
        return {"error": "Slingshot output exceeded the provider response limit."}
    try:
        with open(out_path, encoding="utf-8") as fh:
            result = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {"error": "Slingshot produced an invalid provider result."}
    return result if isinstance(result, dict) else {"error": "Slingshot produced an invalid provider result."}


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
                    "description": "An .h5ad file inside the provider-configured data directory with a reduced embedding in obsm and cluster labels in obs.",
                },
                "embedding_key": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 128,
                    "description": "obsm key of the embedding to build the trajectory on (default 'X_pca'; e.g. 'X_umap').",
                },
                "cluster_key": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 128,
                    "description": "obs column with cluster labels whose centroids are ordered into lineages.",
                },
                "start_cluster": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 128,
                    "description": "Known root cluster to start every lineage from (optional but recommended for directionality).",
                },
                "end_clusters": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 64,
                    "uniqueItems": True,
                    "items": {"type": "string", "minLength": 1, "maxLength": 128},
                    "description": "Known terminal cluster(s) to force as lineage endpoints (optional).",
                },
                "n_dims": {
                    "type": "integer",
                    "minimum": 2,
                    "maximum": 100,
                    "description": "Use only the first n_dims columns of the embedding (default: at most 100; for X_pca, 10-20 is typical).",
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
        try:
            arguments = require_argument_object(arguments)
        except ValueError as exc:
            return {"error": str(exc)}
        adata_path = arguments.get("adata_path")
        cluster_key = arguments.get("cluster_key")
        if not adata_path:
            return {"error": "Missing required parameter: adata_path"}
        if not cluster_key:
            return {"error": "Missing required parameter: cluster_key"}
        try:
            cluster_key = bounded_text(cluster_key, "cluster_key")
            embedding_key = bounded_text(
                arguments.get("embedding_key"), "embedding_key", default="X_pca"
            )
            start_cluster = bounded_text(
                arguments.get("start_cluster"), "start_cluster"
            )
            n_dims = bounded_integer(
                arguments.get("n_dims"), "n_dims", minimum=2, maximum=100
            )
            end_clusters = arguments.get("end_clusters") or []
            if not isinstance(end_clusters, list) or len(end_clusters) > _MAX_CLUSTERS:
                raise ValueError(
                    f"end_clusters must contain at most {_MAX_CLUSTERS} labels."
                )
            if any(
                not isinstance(label, str) or not label or len(label) > 128
                for label in end_clusters
            ) or len(set(end_clusters)) != len(end_clusters):
                raise ValueError("end_clusters must contain unique, bounded strings.")
        except ValueError as exc:
            return {"error": str(exc)}

        try:
            adata = load_remote_h5ad(adata_path, sc.read_h5ad)
        except ValueError as exc:
            return {"error": f"Invalid adata_path: {exc}"}
        if embedding_key not in adata.obsm:
            return {"error": "embedding_key was not found in adata.obsm."}
        if cluster_key not in adata.obs:
            return {"error": "cluster_key was not found in adata.obs."}

        emb = np.asarray(adata.obsm[embedding_key], dtype=float)
        if emb.ndim != 2 or emb.shape[0] != adata.n_obs or emb.shape[1] < 2:
            return {"error": "The requested embedding has an invalid shape."}
        emb = emb[:, :n_dims] if n_dims is not None else emb[:, :100]
        if not np.isfinite(emb).all():
            return {"error": "The requested embedding contains non-finite values."}
        clusters = adata.obs[cluster_key].astype(str).to_numpy()
        cluster_names = set(clusters)
        if not 2 <= len(cluster_names) <= _MAX_CLUSTERS or any(
            not label or len(label) > 128 or "\n" in label or "\r" in label
            for label in clusters
        ):
            return {"error": "cluster_key contains too many or invalid labels."}
        if start_cluster and start_cluster not in cluster_names:
            return {"error": "start_cluster was not found in cluster_key."}
        if not set(end_clusters).issubset(cluster_names):
            return {"error": "One or more end_clusters were not found in cluster_key."}

        with tempfile.TemporaryDirectory() as work:
            np.savetxt(os.path.join(work, "embedding.csv"), emb, delimiter=",")
            with open(os.path.join(work, "clusters.txt"), "w") as fh:
                fh.write("\n".join(clusters))
            config = {
                "start_cluster": start_cluster or "",
                "end_clusters": end_clusters,
                "max_pseudotime_cells": _MAX_PSEUDOTIME_CELLS,
            }
            with open(os.path.join(work, "config.json"), "w") as fh:
                json.dump(config, fh)
            res = _run_rscript(work)

        if "error" in res:
            return res
        lineages = res.get("lineages")
        if (
            not isinstance(lineages, list)
            or not 1 <= len(lineages) <= _MAX_CLUSTERS
            or any(
                not isinstance(lineage, list)
                or len(lineage) > _MAX_CLUSTERS
                or any(
                    not isinstance(label, str) or label not in cluster_names
                    for label in lineage
                )
                for lineage in lineages
            )
        ):
            return {"error": "Slingshot returned invalid lineage output."}
        pseudotime = res.get("pseudotime")
        if pseudotime is not None and (
            not isinstance(pseudotime, list)
            or len(pseudotime) != adata.n_obs
            or any(
                not isinstance(row, list)
                or len(row) != len(lineages)
                or any(
                    value is not None
                    and (
                        isinstance(value, bool)
                        or not isinstance(value, (int, float))
                        or not math.isfinite(value)
                    )
                    for value in row
                )
                for row in pseudotime
            )
        ):
            return {"error": "Slingshot returned invalid pseudotime output."}
        res["model"] = "Slingshot"
        res["embedding_key"] = embedding_key
        res["n_cells"] = int(emb.shape[0])
        if "pseudotime" in res:
            res["cell_ids"] = adata.obs_names.astype(str).tolist()
        return res


if __name__ == "__main__":
    start_mcp_server()
