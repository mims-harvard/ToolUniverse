"""
scVelo single-cell RNA velocity & pseudotime — MCP Server.

scVelo (Bergen et al., Nature Biotechnology 2020) infers RNA velocity from the
ratio of unspliced (nascent) to spliced (mature) mRNA in single-cell RNA-seq.
The velocity field — the predicted direction and rate of transcriptional change
per cell — is projected onto a graph to recover a latent ordering of cells along
differentiation, summarized here as `velocity_pseudotime` plus a per-cell
`velocity_confidence`.

This module exposes scVelo as a ToolUniverse *remote* tool because it carries a
scanpy/scVelo dependency stack (`scvelo` -> scanpy + anndata + numba) that the
core ToolUniverse install keeps light. The computation is moderate; the
per-cluster pseudotime summaries returned are small and bounded.

Inputs are referenced by an ``adata_path`` (a server-accessible ``.h5ad``)
rather than inlined, because single-cell matrices are large. The AnnData MUST
carry **spliced** and **unspliced** layers (e.g. produced by velocyto, kallisto
| bustools / kb-python, or STARsolo). Without them RNA velocity cannot be
estimated and the tool returns a clear error.

One operation is served:
  * run_scvelo_velocity -> per-cell pseudotime + confidence summaries
                           (and mean pseudotime per cluster, a coarse ordering)

References
----------
Bergen V, Lange M, Peidli S, Wolf FA, Theis FJ. "Generalizing RNA velocity to
transient cell states through dynamical modeling." Nature Biotechnology 38,
1408-1414 (2020).
La Manno G, Soldatov R, Zeisel A, et al. "RNA velocity of single cells." Nature
560, 494-498 (2018).
"""

from typing import Any, Dict

import numpy as np
import scanpy as sc  # scvelo builds on scanpy/anndata; also used to read .h5ad
import scvelo as scv

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server

_VALID_MODES = ("deterministic", "stochastic", "dynamical")


def _summarize(values) -> Dict[str, float]:
    """Return bounded summary statistics for a per-cell array."""
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return {"mean": None, "min": None, "max": None, "std": None}
    return {
        "mean": float(arr.mean()),
        "min": float(arr.min()),
        "max": float(arr.max()),
        "std": float(arr.std()),
    }


@register_mcp_tool(
    tool_type_name="run_scvelo_velocity",
    config={
        "description": (
            "Run scVelo (Bergen et al. 2020) RNA-velocity inference on a "
            "single-cell AnnData and return a velocity-derived pseudotime "
            "ordering of cells plus a per-cell velocity confidence. The input "
            ".h5ad MUST contain `spliced` and `unspliced` layers (e.g. from "
            "velocyto or kb-python); without them velocity cannot be estimated. "
            "Pipeline: filter_and_normalize -> moments -> velocity -> "
            "velocity_graph -> velocity_pseudotime + velocity_confidence. "
            "When a cluster_key is supplied, also returns mean pseudotime per "
            "cluster (a coarse trajectory ordering)."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "adata_path": {
                    "type": "string",
                    "description": "Server-accessible path or URL to an .h5ad AnnData that contains `spliced` and `unspliced` layers.",
                },
                "cluster_key": {
                    "type": "string",
                    "description": "obs column to summarize pseudotime by (optional); returns mean velocity_pseudotime per cluster as a coarse ordering.",
                },
                "mode": {
                    "type": "string",
                    "description": "Velocity estimation mode: 'deterministic', 'stochastic' (default), or 'dynamical'.",
                },
            },
            "required": ["adata_path"],
        },
    },
    mcp_config={
        "server_name": "scVelo MCP Server",
        "host": "127.0.0.1",
        "port": 8025,
        "transport": "http",
    },
)
class ScveloVelocityTool:
    """Run scVelo RNA velocity and return pseudotime + confidence summaries."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        adata_path = arguments.get("adata_path")
        if not adata_path:
            return {"error": "Missing required parameter: adata_path"}
        cluster_key = arguments.get("cluster_key") or None
        mode = (arguments.get("mode") or "stochastic").lower()
        if mode not in _VALID_MODES:
            return {
                "error": (
                    f"Invalid mode '{mode}'. Choose one of: {', '.join(_VALID_MODES)}."
                )
            }

        try:
            adata = sc.read_h5ad(adata_path)
        except Exception as exc:  # noqa: BLE001
            return {"error": f"Failed to read adata_path '{adata_path}': {exc}"}

        # RNA velocity requires spliced + unspliced layers.
        missing = [
            layer for layer in ("spliced", "unspliced") if layer not in adata.layers
        ]
        if missing:
            return {
                "error": (
                    "AnnData is missing required layer(s) "
                    f"{missing} for RNA velocity. scVelo needs both `spliced` "
                    "and `unspliced` count layers, e.g. produced by velocyto, "
                    "kb-python (kallisto|bustools), or STARsolo. "
                    f"Available layers: {list(adata.layers.keys())}."
                )
            }

        if cluster_key is not None and cluster_key not in adata.obs:
            return {
                "error": (
                    f"cluster_key '{cluster_key}' not found in adata.obs. "
                    f"Available columns: {list(adata.obs.columns)}"
                )
            }

        try:
            # filter + normalize + log (no n_top_genes: scVelo routes it through
            # **kwargs into normalize_per_cell, which rejects it on 0.3.x; HVG
            # subsetting is only a speed optimization, not needed for correctness).
            scv.pp.filter_and_normalize(adata, min_shared_counts=20)
            scv.pp.moments(adata, n_pcs=30, n_neighbors=30)
            if mode == "dynamical":
                # Dynamical mode requires the recovered latent gene dynamics.
                scv.tl.recover_dynamics(adata)
            scv.tl.velocity(adata, mode=mode)
            scv.tl.velocity_graph(adata)
            scv.tl.velocity_pseudotime(adata)
            scv.tl.velocity_confidence(adata)
        except Exception as exc:  # noqa: BLE001
            return {"error": f"scVelo velocity computation failed: {exc}"}

        n_cells = int(adata.n_obs)
        pseudotime = adata.obs.get("velocity_pseudotime")
        confidence = adata.obs.get("velocity_confidence")
        if pseudotime is None:
            return {"error": "scVelo did not write velocity_pseudotime."}

        result: Dict[str, Any] = {
            "n_cells": n_cells,
            "mode": mode,
            "mean_pseudotime": _summarize(pseudotime)["mean"],
            "pseudotime_summary": _summarize(pseudotime),
            "mean_confidence": (
                _summarize(confidence)["mean"] if confidence is not None else None
            ),
            "confidence_summary": (
                _summarize(confidence) if confidence is not None else None
            ),
        }

        # Mean pseudotime per cluster — a coarse trajectory ordering.
        if cluster_key is not None:
            grouped = (
                adata.obs.groupby(cluster_key, observed=True)["velocity_pseudotime"]
                .mean()
                .sort_values()
            )
            result["pseudotime_by_cluster"] = {
                str(k): float(v) for k, v in grouped.items()
            }
            result["cluster_key"] = cluster_key

        # Only return the full per-cell arrays for small datasets.
        if n_cells <= 500:
            result["pseudotime"] = [
                float(x) for x in np.asarray(pseudotime, dtype=float)
            ]
            if confidence is not None:
                result["confidence"] = [
                    float(x) for x in np.asarray(confidence, dtype=float)
                ]

        ordering = ""
        if cluster_key is not None and result.get("pseudotime_by_cluster"):
            ordering = (
                " Coarse cluster ordering (early -> late): "
                + " -> ".join(result["pseudotime_by_cluster"].keys())
                + "."
            )
        result["note"] = (
            f"scVelo '{mode}' velocity on {n_cells} cells. "
            "velocity_pseudotime orders cells along the inferred differentiation; "
            "velocity_confidence (0-1) reflects local coherence of the velocity "
            "field." + ordering
        )
        return result


if __name__ == "__main__":
    start_mcp_server()
