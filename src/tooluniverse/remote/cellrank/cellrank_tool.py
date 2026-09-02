"""
CellRank single-cell fate mapping — MCP Server.

CellRank 2 (Weiler, Lange, Klein et al., Nature Methods 2024; original CellRank:
Lange et al., Nature Methods 2022) infers cellular fate from single-cell data. It
builds a Markov transition matrix over cells with a *kernel* (RNA velocity,
connectivity, or pseudotime), then a GPCCA *estimator* coarse-grains that matrix
into macrostates, identifies the terminal (and initial) states, and computes,
for every cell, its probability of reaching each terminal state — the standard
readout for differentiation/lineage analysis.

This module exposes CellRank as a ToolUniverse *remote* tool because it carries a
heavy single-cell dependency stack (`cellrank` -> scanpy/anndata + scikit-learn +
pyGPCCA + optionally scVelo). Running it on a dedicated server keeps the core
ToolUniverse install light.

Inputs are referenced by an ``adata_path`` (a server-accessible ``.h5ad``) rather
than inlined, because single-cell matrices are large. The kernel is selectable:
  * ``connectivity`` (default) — needs only a kNN graph (broadest applicability)
  * ``pseudotime``            — needs a precomputed pseudotime in ``obs``
  * ``velocity``              — needs precomputed RNA velocity (scVelo) layers

One operation is served:
  * run_cellrank_fate -> terminal macrostates + per-cell fate probabilities

References
----------
Weiler P, Lange M, Klein M, Pe'er D, Theis FJ. "CellRank 2: unified fate mapping
in multiview single-cell data." Nature Methods 21, 1196-1205 (2024).
Lange M, Bergen V, Klein M, et al. "CellRank for directed single-cell fate
mapping." Nature Methods 19, 159-170 (2022).
"""

from typing import Any, Dict

import numpy as np
import scanpy as sc
import cellrank as cr

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server
from tooluniverse.remote_argument_validation import (
    bounded_integer,
    bounded_text,
    require_argument_object,
)
from tooluniverse.remote_data_path import load_remote_h5ad

_VALID_KERNELS = ("connectivity", "pseudotime", "velocity")

# Above this cell count, the per-cell fate-probability matrix is omitted from the
# response to keep the payload bounded; only the per-cluster summary is returned.
_CELL_ARRAY_LIMIT = 5000


def _ensure_graph(adata):
    """Make sure a kNN graph exists (PCA + neighbors), computing it if absent."""
    if "neighbors" not in adata.uns:
        if "X_pca" not in adata.obsm:
            n_comps = min(50, adata.n_vars - 1, adata.n_obs - 1)
            sc.pp.pca(adata, n_comps=n_comps)
        sc.pp.neighbors(adata, n_neighbors=15)


def _build_kernel(adata, kernel: str, pseudotime_key: str):
    """Construct a CellRank kernel and its transition matrix."""
    if kernel == "velocity":
        from cellrank.kernels import VelocityKernel

        return VelocityKernel(adata).compute_transition_matrix()
    if kernel == "pseudotime":
        from cellrank.kernels import PseudotimeKernel

        return PseudotimeKernel(
            adata, time_key=pseudotime_key
        ).compute_transition_matrix()
    from cellrank.kernels import ConnectivityKernel

    return ConnectivityKernel(adata).compute_transition_matrix()


@register_mcp_tool(
    tool_type_name="run_cellrank_fate",
    config={
        "description": (
            "Map single-cell fate with CellRank 2: build a Markov transition "
            "matrix over cells (kernel = connectivity / pseudotime / velocity), "
            "coarse-grain it with a GPCCA estimator to find terminal macrostates, "
            "and compute each cell's probability of reaching each terminal state. "
            "Returns the terminal states and the per-cell fate-probability matrix "
            "(plus per-cluster mean fate probabilities when a cluster key is given)."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "adata_path": {
                    "type": "string",
                    "description": "An .h5ad file inside the provider-configured data directory (log-normalized; raw velocity layers required only for kernel='velocity').",
                },
                "kernel": {
                    "type": "string",
                    "enum": ["connectivity", "pseudotime", "velocity"],
                    "description": "Transition kernel: 'connectivity' (default; kNN graph only), 'pseudotime' (needs pseudotime_key), or 'velocity' (needs scVelo velocity layers).",
                },
                "n_states": {
                    "type": "integer",
                    "minimum": 2,
                    "maximum": 20,
                    "description": "Number of macrostates to compute (default 3); terminal states are auto-selected from these.",
                },
                "pseudotime_key": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 128,
                    "description": "obs column with a precomputed pseudotime (required when kernel='pseudotime', e.g. 'dpt_pseudotime').",
                },
                "cluster_key": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 128,
                    "description": "obs column with cluster/cell-type labels; used to name macrostates and to report per-cluster mean fate probabilities (optional).",
                },
            },
            "required": ["adata_path"],
        },
    },
    mcp_config={
        "server_name": "CellRank Fate Mapping MCP Server",
        "host": "127.0.0.1",
        "port": 8028,
        "transport": "http",
    },
)
class CellrankFateTool:
    """Compute terminal states and per-cell fate probabilities with CellRank 2."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            arguments = require_argument_object(arguments)
        except ValueError as exc:
            return {"error": str(exc)}
        adata_path = arguments.get("adata_path")
        if not adata_path:
            return {"error": "Missing required parameter: adata_path"}
        try:
            raw_kernel = arguments.get("kernel")
            if raw_kernel is not None and not isinstance(raw_kernel, str):
                raise ValueError("kernel must be a string.")
            kernel = bounded_text(
                raw_kernel.lower() if raw_kernel else None,
                "kernel",
                default="connectivity",
                maximum=12,
                allowed=_VALID_KERNELS,
            )
            n_states = bounded_integer(
                arguments.get("n_states"),
                "n_states",
                default=3,
                minimum=2,
                maximum=20,
            )
            pseudotime_key = bounded_text(
                arguments.get("pseudotime_key"), "pseudotime_key"
            )
            cluster_key = bounded_text(arguments.get("cluster_key"), "cluster_key")
        except ValueError as exc:
            return {"error": str(exc)}

        try:
            adata = load_remote_h5ad(adata_path, sc.read_h5ad)
        except ValueError as exc:
            return {"error": f"Invalid adata_path: {exc}"}
        if kernel == "pseudotime":
            if not pseudotime_key:
                return {"error": "kernel='pseudotime' requires pseudotime_key."}
            if pseudotime_key not in adata.obs:
                return {"error": f"pseudotime_key '{pseudotime_key}' not in adata.obs."}
        if kernel == "velocity":
            missing = [ly for ly in ("Ms", "velocity") if ly not in adata.layers]
            if missing:
                return {
                    "error": (
                        f"kernel='velocity' requires precomputed RNA velocity "
                        f"(missing adata.layers{missing}). Run scVelo first "
                        "(scv.pp.moments + scv.tl.velocity, e.g. via the scVelo "
                        "remote tool), or use kernel='connectivity'/'pseudotime'."
                    )
                }
        if cluster_key and cluster_key not in adata.obs:
            return {"error": f"cluster_key '{cluster_key}' not in adata.obs."}
        if adata.n_obs <= n_states:
            return {"error": "n_states must be smaller than the number of cells."}

        try:
            _ensure_graph(adata)
            kobj = _build_kernel(adata, kernel, pseudotime_key)
            estimator = cr.estimators.GPCCA(kobj)
            n_comps = min(max(n_states + 2, 10), adata.n_obs - 1)
            estimator.compute_schur(n_components=n_comps)
            estimator.compute_macrostates(n_states=n_states, cluster_key=cluster_key)
            estimator.predict_terminal_states()
            estimator.compute_fate_probabilities(n_jobs=1, show_progress_bar=False)
            fate = estimator.fate_probabilities
            terminal_names = [str(name) for name in fate.names]
            probs = np.asarray(fate, dtype=float)
        except Exception:
            return {"error": "CellRank fate mapping failed on the provider."}
        n_cells = int(probs.shape[0])
        if (
            probs.ndim != 2
            or n_cells != adata.n_obs
            or probs.shape[1] != len(terminal_names)
            or not 1 <= len(terminal_names) <= n_states
            or any(not name or len(name) > 128 for name in terminal_names)
            or not np.isfinite(probs).all()
            or (probs < -1e-8).any()
            or (probs > 1 + 1e-8).any()
        ):
            return {"error": "CellRank returned invalid fate probabilities."}

        result = {
            "model": "CellRank 2",
            "kernel": kernel,
            "n_cells": n_cells,
            "n_macrostates": int(n_states),
            "terminal_states": terminal_names,
            "n_terminal_states": len(terminal_names),
        }
        # Per-cluster mean fate probabilities (compact, always useful)
        if cluster_key:
            labels = adata.obs[cluster_key].astype(str).to_numpy()
            if len(set(labels)) > 256 or any(not label or len(label) > 128 for label in labels):
                return {"error": "cluster_key contains too many or invalid labels."}
            per_cluster = {}
            for lab in sorted(set(labels)):
                m = labels == lab
                per_cluster[lab] = {
                    name: float(probs[m, k].mean())
                    for k, name in enumerate(terminal_names)
                }
            result["mean_fate_probabilities_by_cluster"] = per_cluster
        # Full per-cell matrix only when small enough to serialize sensibly
        if n_cells <= _CELL_ARRAY_LIMIT:
            result["fate_probabilities"] = probs.tolist()
            result["cell_ids"] = adata.obs_names.astype(str).tolist()
        else:
            result["note"] = (
                f"{n_cells} cells > {_CELL_ARRAY_LIMIT}: per-cell fate_probabilities "
                "omitted; use mean_fate_probabilities_by_cluster (supply cluster_key)."
            )
        return result


if __name__ == "__main__":
    start_mcp_server()
