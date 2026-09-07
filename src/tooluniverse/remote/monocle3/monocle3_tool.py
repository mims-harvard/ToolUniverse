"""
Monocle3 pseudotime / trajectory inference — MCP Server.

Monocle3 (Cao et al., Nature 2019; Trapnell lab) reconstructs single-cell
developmental trajectories by learning a principal graph through a UMAP
embedding and ordering cells in pseudotime from a chosen root. Unlike Slingshot
(which orders pre-computed clusters), Monocle3 learns its own graph — including
loops and branch points — and is the standard Trapnell-lab pseudotime tool.

Served as a ToolUniverse *remote* tool because the engine is R/Bioconductor
(`monocle3`). The Python side reads the ``.h5ad`` with scanpy and hands the
**raw count** matrix to a bundled R script (MatrixMarket interchange — no
zellkonverter/basilisk); the script builds a cell_data_set, runs the standard
preprocess -> reduce_dimension -> cluster_cells -> learn_graph -> order_cells
pipeline, and returns per-cell pseudotime as JSON.

Specify the trajectory root with ``root_cluster`` (all cells of a named input
cluster, requires ``cluster_key``) or explicit ``root_cells``.

One operation:
  * run_monocle3_pseudotime -> per-cell pseudotime along the learned graph

Reference
---------
Cao J, Spielmann M, Qiu X, et al. "The single-cell transcriptional landscape of
mammalian organogenesis." Nature 566, 496-502 (2019).
"""

import json
import math
import os
import subprocess
import tempfile
from typing import Any, Dict

import scanpy as sc
from scipy.io import mmwrite
from scipy.sparse import csr_matrix

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server
from tooluniverse.remote_argument_validation import (
    bounded_integer,
    bounded_text,
    require_argument_object,
)
from tooluniverse.remote_data_path import load_remote_h5ad

_R_SCRIPT = os.path.join(os.path.dirname(__file__), "monocle3_pseudotime.R")
_RSCRIPT = os.environ.get("RSCRIPT_BIN", "Rscript")
_TIMEOUT = 1800
_MAX_PSEUDOTIME_CELLS = 50000
_MAX_ROOT_CELLS = 1000
_MAX_OUTPUT_BYTES = 25_000_000


def _run_rscript(work: str) -> Dict[str, Any]:
    """Run the bundled Monocle3 R script over a prepared work dir; return parsed JSON."""
    if not os.path.exists(_R_SCRIPT):
        return {"error": "The provider's bundled Monocle3 script is unavailable."}
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
        return {"error": f"Monocle3 timed out after {_TIMEOUT}s."}
    except OSError:
        return {"error": "The provider could not start Monocle3."}
    out_path = os.path.join(work, "output.json")
    if proc.returncode != 0 or not os.path.exists(out_path):
        return {"error": f"Monocle3 failed on the provider (returncode {proc.returncode})."}
    if os.path.getsize(out_path) > _MAX_OUTPUT_BYTES:
        return {"error": "Monocle3 output exceeded the provider response limit."}
    try:
        with open(out_path, encoding="utf-8") as fh:
            result = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {"error": "Monocle3 produced an invalid provider result."}
    return result if isinstance(result, dict) else {"error": "Monocle3 produced an invalid provider result."}


@register_mcp_tool(
    tool_type_name="run_monocle3_pseudotime",
    config={
        "description": (
            "Infer single-cell pseudotime with Monocle3 (Cao 2019): build a "
            "cell_data_set from raw counts, run the standard preprocess -> UMAP -> "
            "cluster -> learn_graph -> order_cells pipeline, and return each cell's "
            "pseudotime along the learned principal graph. Monocle3 learns its own "
            "graph (branches/loops) rather than ordering preset clusters. If the "
            "upstream loop-closing stage fails, the provider reports an acyclic "
            "graph fallback in graph_learning. Specify the root with root_cluster "
            "(+ cluster_key) or explicit root_cells."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "adata_path": {
                    "type": "string",
                    "description": "An .h5ad file of raw counts inside the provider-configured data directory (Monocle3 normalizes internally).",
                },
                "counts_layer": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 128,
                    "description": "layers key holding raw counts if .X is not raw (optional; default: use .X).",
                },
                "cluster_key": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 128,
                    "description": "obs column with input cluster labels; required when rooting via root_cluster, and enables per-cluster mean pseudotime.",
                },
                "root_cluster": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 128,
                    "description": "Name of the input cluster (in cluster_key) whose cells are the trajectory root.",
                },
                "root_cells": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 1000,
                    "uniqueItems": True,
                    "items": {"type": "string", "minLength": 1, "maxLength": 256},
                    "description": "Explicit root cell ids (obs_names); alternative to root_cluster.",
                },
                "num_dim": {
                    "type": "integer",
                    "minimum": 2,
                    "maximum": 100,
                    "description": "PCA dimensions for preprocess_cds (default 50).",
                },
            },
            "required": ["adata_path"],
        },
    },
    mcp_config={
        "server_name": "Monocle3 Pseudotime MCP Server",
        "host": "127.0.0.1",
        "port": 8031,
        "transport": "http",
    },
)
class Monocle3PseudotimeTool:
    """Learn a trajectory graph and order cells in pseudotime with Monocle3."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            arguments = require_argument_object(arguments)
        except ValueError as exc:
            return {"error": str(exc)}
        adata_path = arguments.get("adata_path")
        if not adata_path:
            return {"error": "Missing required parameter: adata_path"}
        try:
            root_cluster = bounded_text(arguments.get("root_cluster"), "root_cluster")
            cluster_key = bounded_text(arguments.get("cluster_key"), "cluster_key")
            counts_layer = bounded_text(arguments.get("counts_layer"), "counts_layer")
            num_dim = bounded_integer(
                arguments.get("num_dim"),
                "num_dim",
                default=50,
                minimum=2,
                maximum=100,
            )
            root_cells = arguments.get("root_cells") or []
            if not isinstance(root_cells, list) or not 1 <= len(root_cells) <= _MAX_ROOT_CELLS:
                if arguments.get("root_cells") is not None:
                    raise ValueError(
                        f"root_cells must contain between 1 and {_MAX_ROOT_CELLS} cell ids."
                    )
                root_cells = []
            if any(
                not isinstance(cell, str) or not cell or len(cell) > 256
                for cell in root_cells
            ) or len(set(root_cells)) != len(root_cells):
                raise ValueError("root_cells must contain unique, bounded string ids.")
        except ValueError as exc:
            return {"error": str(exc)}
        if not root_cluster and not root_cells:
            return {
                "error": "Provide root_cluster (with cluster_key) or root_cells to orient pseudotime."
            }
        if root_cluster and not cluster_key:
            return {
                "error": "root_cluster requires cluster_key (the obs column holding cluster labels)."
            }
        if root_cluster and root_cells:
            return {"error": "Provide either root_cluster or root_cells, not both."}

        try:
            adata = load_remote_h5ad(adata_path, sc.read_h5ad)
        except ValueError as exc:
            return {"error": f"Invalid adata_path: {exc}"}
        if counts_layer and counts_layer not in adata.layers:
            return {"error": "counts_layer was not found in adata.layers."}
        if cluster_key and cluster_key not in adata.obs:
            return {"error": "cluster_key was not found in adata.obs."}
        cell_ids = [str(cell) for cell in adata.obs_names]
        if any(not cell or len(cell) > 256 or "\n" in cell or "\r" in cell for cell in cell_ids):
            return {"error": "AnnData contains an invalid cell id."}
        gene_ids = [str(gene) for gene in adata.var_names]
        if any(not gene or len(gene) > 256 or "\n" in gene or "\r" in gene for gene in gene_ids):
            return {"error": "AnnData contains an invalid gene id."}
        if root_cells and not set(root_cells).issubset(cell_ids):
            return {"error": "One or more root_cells were not found in the dataset."}
        if cluster_key:
            cluster_values = adata.obs[cluster_key].astype(str).tolist()
            if len(set(cluster_values)) > 256 or any(
                not value or len(value) > 128 or "\n" in value or "\r" in value
                for value in cluster_values
            ):
                return {"error": "cluster_key contains too many or invalid labels."}
            if root_cluster and root_cluster not in set(cluster_values):
                return {"error": "root_cluster was not found in cluster_key."}

        matrix = adata.layers[counts_layer] if counts_layer else adata.X
        with tempfile.TemporaryDirectory() as work:
            mmwrite(
                os.path.join(work, "expr.mtx"), csr_matrix(matrix).T
            )  # genes x cells
            with open(os.path.join(work, "genes.txt"), "w") as fh:
                fh.write("\n".join(gene_ids))
            with open(os.path.join(work, "cells.txt"), "w") as fh:
                fh.write("\n".join(cell_ids))
            if cluster_key:
                with open(os.path.join(work, "clusters.txt"), "w") as fh:
                    fh.write("\n".join(cluster_values))
            config = {
                "num_dim": num_dim,
                "root_cluster": root_cluster or "",
                "root_cells": [str(c) for c in root_cells],
                "max_pseudotime_cells": _MAX_PSEUDOTIME_CELLS,
            }
            with open(os.path.join(work, "config.json"), "w") as fh:
                json.dump(config, fh)
            res = _run_rscript(work)

        if "error" in res:
            return res
        n_cells = res.get("n_cells")
        pseudotime = res.get("pseudotime")
        returned_cells = res.get("cell_ids")
        if n_cells != adata.n_obs:
            return {"error": "Monocle3 returned an invalid cell count."}
        if pseudotime is not None and (
            not isinstance(pseudotime, list)
            or len(pseudotime) != n_cells
            or any(
                value is not None
                and (not isinstance(value, (int, float)) or not math.isfinite(value))
                for value in pseudotime
            )
        ):
            return {"error": "Monocle3 returned invalid pseudotime values."}
        if returned_cells is not None and returned_cells != cell_ids:
            return {"error": "Monocle3 returned misaligned cell ids."}
        res["model"] = "Monocle3"
        return res


if __name__ == "__main__":
    start_mcp_server()
