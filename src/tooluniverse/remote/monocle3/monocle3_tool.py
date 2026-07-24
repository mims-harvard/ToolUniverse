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
import os
import subprocess
import tempfile
from typing import Any, Dict

import scanpy as sc
from scipy.io import mmwrite
from scipy.sparse import csr_matrix

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server

_R_SCRIPT = os.path.join(os.path.dirname(__file__), "monocle3_pseudotime.R")
_RSCRIPT = os.environ.get("RSCRIPT_BIN", "Rscript")
_TIMEOUT = 1800
_MAX_PSEUDOTIME_CELLS = 50000


def _run_rscript(work: str) -> Dict[str, Any]:
    """Run the bundled Monocle3 R script over a prepared work dir; return parsed JSON."""
    if not os.path.exists(_R_SCRIPT):
        return {"error": f"Monocle3 R script not found at {_R_SCRIPT}."}
    try:
        proc = subprocess.run(
            [_RSCRIPT, _R_SCRIPT, work],
            capture_output=True,
            text=True,
            timeout=_TIMEOUT,
        )
    except FileNotFoundError:
        return {
            "error": f"Rscript not found ('{_RSCRIPT}'); install R + the monocle3 package."
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Monocle3 timed out after {_TIMEOUT}s."}
    out_path = os.path.join(work, "output.json")
    if proc.returncode != 0 or not os.path.exists(out_path):
        return {
            "error": f"Monocle3 (R) failed: {proc.stderr[-600:] or proc.stdout[-600:]}"
        }
    with open(out_path) as fh:
        return json.load(fh)


@register_mcp_tool(
    tool_type_name="run_monocle3_pseudotime",
    config={
        "description": (
            "Infer single-cell pseudotime with Monocle3 (Cao 2019): build a "
            "cell_data_set from raw counts, run the standard preprocess -> UMAP -> "
            "cluster -> learn_graph -> order_cells pipeline, and return each cell's "
            "pseudotime along the learned principal graph. Monocle3 learns its own "
            "graph (branches/loops) rather than ordering preset clusters. Specify "
            "the root with root_cluster (+ cluster_key) or explicit root_cells."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "adata_path": {
                    "type": "string",
                    "description": "Server-accessible path to an .h5ad AnnData of RAW counts (Monocle3 normalizes internally).",
                },
                "counts_layer": {
                    "type": "string",
                    "description": "layers key holding raw counts if .X is not raw (optional; default: use .X).",
                },
                "cluster_key": {
                    "type": "string",
                    "description": "obs column with input cluster labels; required when rooting via root_cluster, and enables per-cluster mean pseudotime.",
                },
                "root_cluster": {
                    "type": "string",
                    "description": "Name of the input cluster (in cluster_key) whose cells are the trajectory root.",
                },
                "root_cells": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Explicit root cell ids (obs_names); alternative to root_cluster.",
                },
                "num_dim": {
                    "type": "integer",
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
        adata_path = arguments.get("adata_path")
        if not adata_path:
            return {"error": "Missing required parameter: adata_path"}
        root_cluster = arguments.get("root_cluster") or None
        root_cells = arguments.get("root_cells") or []
        cluster_key = arguments.get("cluster_key") or None
        if not root_cluster and not root_cells:
            return {
                "error": "Provide root_cluster (with cluster_key) or root_cells to orient pseudotime."
            }
        if root_cluster and not cluster_key:
            return {
                "error": "root_cluster requires cluster_key (the obs column holding cluster labels)."
            }

        adata = sc.read_h5ad(adata_path)
        counts_layer = arguments.get("counts_layer") or None
        if counts_layer and counts_layer not in adata.layers:
            return {"error": f"counts_layer '{counts_layer}' not in adata.layers."}
        if cluster_key and cluster_key not in adata.obs:
            return {"error": f"cluster_key '{cluster_key}' not in adata.obs."}

        matrix = adata.layers[counts_layer] if counts_layer else adata.X
        with tempfile.TemporaryDirectory() as work:
            mmwrite(
                os.path.join(work, "expr.mtx"), csr_matrix(matrix).T
            )  # genes x cells
            with open(os.path.join(work, "genes.txt"), "w") as fh:
                fh.write("\n".join(str(g) for g in adata.var_names))
            with open(os.path.join(work, "cells.txt"), "w") as fh:
                fh.write("\n".join(str(c) for c in adata.obs_names))
            if cluster_key:
                with open(os.path.join(work, "clusters.txt"), "w") as fh:
                    fh.write("\n".join(adata.obs[cluster_key].astype(str)))
            config = {
                "num_dim": int(arguments.get("num_dim") or 50),
                "root_cluster": root_cluster or "",
                "root_cells": [str(c) for c in root_cells],
                "max_pseudotime_cells": _MAX_PSEUDOTIME_CELLS,
            }
            with open(os.path.join(work, "config.json"), "w") as fh:
                json.dump(config, fh)
            res = _run_rscript(work)

        if "error" in res:
            return res
        res["model"] = "Monocle3"
        return res


if __name__ == "__main__":
    start_mcp_server()
