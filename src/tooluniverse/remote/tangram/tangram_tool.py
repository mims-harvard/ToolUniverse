"""
Tangram spatial-transcriptomics cell mapping / deconvolution — MCP Server.

Tangram (Biancalani et al., Nature Methods 2021) aligns single-cell RNA-seq
data onto a spatial-transcriptomics assay by learning, for every single cell,
a probability of mapping to each spatial voxel/spot. In ``clusters`` mode it
maps cell-type clusters (rather than individual cells) onto space and the
resulting mapping can be projected back to per-spot cell-type scores — i.e. a
spatial *deconvolution* of each spot into its constituent cell types.

This module exposes Tangram as a ToolUniverse *remote* tool because it carries
a heavy dependency stack (`tangram-sc` -> PyTorch + scanpy/anndata). Running it
on a dedicated server keeps the core ToolUniverse install light; mapping runs
on CPU for the modest reference/spatial matrices typical of this workflow.

Inputs are referenced by paths (server-accessible ``.h5ad`` files) rather than
inlined, because single-cell and spatial matrices are large:
  * ``sc_path`` -> single-cell reference AnnData (with `cluster_label` in obs)
  * ``sp_path`` -> spatial AnnData (spots x genes)

One operation is served:
  * run_tangram_deconvolution -> per-spot cell-type proportions for the spatial
                                 data, derived from a single-cell reference.

References
----------
Biancalani T, Scalia G, Buffoni L, et al. "Deep learning and alignment of
spatially resolved single-cell transcriptomes with Tangram." Nature Methods 18,
1352-1362 (2021).
"""

from typing import Any, Dict

import numpy as np
import scanpy as sc
import tangram as tg

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server
from tooluniverse.remote_argument_validation import (
    bounded_integer,
    bounded_text,
    require_argument_object,
)
from tooluniverse.remote_data_path import load_remote_h5ad


_MAX_CELL_TYPES = 128


@register_mcp_tool(
    tool_type_name="run_tangram_deconvolution",
    config={
        "description": (
            "Deconvolve a spatial-transcriptomics assay into per-spot cell-type "
            "proportions using Tangram (Biancalani 2021). Maps cell-type "
            "clusters from a single-cell reference AnnData onto the spatial "
            "AnnData (clusters mode) and projects the cell-type annotations to "
            "space, returning each spot's cell-type composition. Inputs are "
            "server-accessible .h5ad files."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "sc_path": {
                    "type": "string",
                    "description": "A single-cell reference .h5ad file inside the provider-configured data directory; obs must contain `cluster_label`.",
                },
                "sp_path": {
                    "type": "string",
                    "description": "A spatial .h5ad file inside the provider-configured data directory (spots x genes) to deconvolve.",
                },
                "cluster_label": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 128,
                    "description": "obs column in the single-cell reference naming the cell type/cluster (e.g. 'cell_type').",
                },
                "num_epochs": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5000,
                    "description": "Tangram mapping epochs (default 500).",
                },
            },
            "required": ["sc_path", "sp_path", "cluster_label"],
        },
    },
    mcp_config={
        "server_name": "Tangram MCP Server",
        "host": "127.0.0.1",
        "port": 8018,
        "transport": "http",
    },
)
class TangramDeconvolutionTool:
    """Map a single-cell reference onto a spatial assay and return per-spot cell-type proportions."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            arguments = require_argument_object(arguments)
        except ValueError as exc:
            return {"error": str(exc)}
        sc_path = arguments.get("sc_path")
        sp_path = arguments.get("sp_path")
        cluster_label = arguments.get("cluster_label")
        if not (sc_path and sp_path and cluster_label):
            return {
                "error": "Missing required parameter(s): sc_path, sp_path, cluster_label"
            }
        try:
            cluster_label = bounded_text(cluster_label, "cluster_label")
            num_epochs = bounded_integer(
                arguments.get("num_epochs"),
                "num_epochs",
                default=500,
                minimum=1,
                maximum=5_000,
            )
        except ValueError as exc:
            return {"error": str(exc)}

        try:
            adata_sc = load_remote_h5ad(sc_path, sc.read_h5ad)
            adata_sp = load_remote_h5ad(sp_path, sc.read_h5ad)
        except Exception as exc:  # noqa: BLE001
            return {"error": f"Failed to load AnnData input(s): {exc}"}

        if cluster_label not in adata_sc.obs:
            return {"error": "cluster_label was not found in the reference obs."}
        reference_types = adata_sc.obs[cluster_label].astype(str).unique().tolist()
        if len(reference_types) < 2 or len(reference_types) > _MAX_CELL_TYPES:
            return {
                "error": (
                    f"cluster_label must contain between 2 and "
                    f"{_MAX_CELL_TYPES} cell types."
                )
            }
        if any(not label or len(label) > 128 for label in reference_types):
            return {"error": "cluster_label contains an invalid cell-type label."}

        try:
            # Pick shared training genes and align the two AnnData objects.
            tg.pp_adatas(adata_sc, adata_sp, genes=None)

            ad_map = tg.map_cells_to_space(
                adata_sc,
                adata_sp,
                mode="clusters",
                cluster_label=cluster_label,
                density_prior="rna_count_based",
                num_epochs=num_epochs,
                device="cpu",
            )

            # Project cell-type annotations to space; writes a spots x cell_types
            # DataFrame to adata_sp.obsm["tangram_ct_pred"].
            tg.project_cell_annotations(ad_map, adata_sp, annotation=cluster_label)
        except Exception:  # noqa: BLE001
            return {"error": "Tangram mapping failed on the provider."}

        ct_pred = adata_sp.obsm.get("tangram_ct_pred")
        if ct_pred is None:
            return {"error": "Tangram did not produce 'tangram_ct_pred' output."}

        # Normalize each spot's cell-type scores to proportions summing to 1.
        cell_types = [str(c) for c in ct_pred.columns]
        scores = np.asarray(ct_pred.values, dtype=float)
        if (
            scores.ndim != 2
            or scores.shape[0] != adata_sp.n_obs
            or scores.shape[1] != len(cell_types)
            or not 1 <= len(cell_types) <= _MAX_CELL_TYPES
            or len(set(cell_types)) != len(cell_types)
            or any(not label or len(label) > 128 for label in cell_types)
            or not np.isfinite(scores).all()
        ):
            return {"error": "Tangram returned an invalid deconvolution matrix."}
        scores = np.clip(scores, 0.0, None)
        row_sums = scores.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1.0
        proportions = scores / row_sums

        n_spots = int(proportions.shape[0])
        mean_props = proportions.mean(axis=0)
        mean_proportions = {ct: float(mean_props[i]) for i, ct in enumerate(cell_types)}

        result: Dict[str, Any] = {
            "model": "Tangram",
            "n_spots": n_spots,
            "n_cell_types": len(cell_types),
            "cell_types": cell_types,
            "cluster_label": cluster_label,
            "num_epochs": num_epochs,
            "mean_proportions": mean_proportions,
        }

        # Keep output bounded: emit the full spots x cell_types matrix only for
        # modest spatial assays; otherwise return a compact per-cell-type summary.
        max_rows = 2000
        if n_spots <= max_rows:
            result["spot_ids"] = adata_sp.obs_names.astype(str).tolist()
            result["deconvolution"] = proportions.round(4).tolist()
        else:
            result["deconvolution_summary"] = {
                "note": (
                    f"{n_spots} spots exceeds the {max_rows}-row inline cap; "
                    "returning per-cell-type summary statistics instead of the "
                    "full matrix."
                ),
                "per_cell_type": {
                    ct: {
                        "mean": float(proportions[:, i].mean()),
                        "min": float(proportions[:, i].min()),
                        "max": float(proportions[:, i].max()),
                    }
                    for i, ct in enumerate(cell_types)
                },
            }
        return result


if __name__ == "__main__":
    start_mcp_server()
