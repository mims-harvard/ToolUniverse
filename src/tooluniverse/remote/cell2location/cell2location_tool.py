"""
cell2location spatial cell-type deconvolution — MCP Server.

cell2location (Kleshchevnikov et al., Nature Biotechnology 2022) is a principled
Bayesian model that maps fine-grained cell types onto spatial transcriptomics
data (e.g. 10x Visium) by deconvolving each spatial location into a mixture of
reference cell-type abundances. It is a TWO-step procedure:

  1. Reference signatures — a negative-binomial regression model (RegressionModel)
     is trained on an annotated single-cell/single-nucleus reference to estimate
     per-cell-type expression signatures (``inf_aver``).
  2. Spatial mapping — the Cell2location model is trained on the spatial data
     using those reference signatures to estimate the absolute abundance of every
     cell type at every spatial location (``q05_cell_abundance_w_sf``).

This module exposes cell2location as a ToolUniverse *remote* tool because it
carries a heavy probabilistic deep-learning dependency stack (``cell2location``
-> scvi-tools -> PyTorch + Lightning + Pyro + scanpy/anndata). Running it on a
dedicated server keeps the core ToolUniverse install light. Training is
GPU-recommended; on CPU it is slow, so epoch counts default LOW (250 each) and
should be raised on a GPU for production-quality posteriors.

Inputs are referenced by server-accessible ``.h5ad`` paths (``sc_path`` for the
annotated reference, ``sp_path`` for the spatial data) rather than inlined,
because single-cell/spatial matrices are large.

One operation is served:
  * run_cell2location_deconvolution -> per-spot cell-type abundance summary

References
----------
Kleshchevnikov V, Shmatko A, Dann E, et al. "Cell2location maps fine-grained
cell types in spatial transcriptomics." Nature Biotechnology 40, 661-671 (2022).
"""

from typing import Any, Dict

import numpy as np
import scanpy as sc
import cell2location
from cell2location.models import RegressionModel

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server
from tooluniverse.remote_argument_validation import (
    bounded_integer,
    bounded_text,
    require_argument_object,
)
from tooluniverse.remote_data_path import load_remote_h5ad


_MAX_CELL_TYPES = 256


def _estimate_reference_signatures(adata_ref, cluster_label, batch_key, ref_epochs):
    """Train the RegressionModel and return per-cell-type signature DataFrame (inf_aver)."""
    RegressionModel.setup_anndata(
        adata_ref,
        batch_key=batch_key if batch_key else None,
        labels_key=cluster_label,
    )
    mod = RegressionModel(adata_ref)
    mod.train(max_epochs=ref_epochs)
    adata_ref = mod.export_posterior(
        adata_ref, sample_kwargs={"num_samples": 1000, "batch_size": 2500}
    )

    # Per-cell-type expression signatures (genes x cell types).
    if "means_per_cluster_mu_fg" in adata_ref.varm:
        inf_aver = adata_ref.varm["means_per_cluster_mu_fg"][
            [
                f"means_per_cluster_mu_fg_{ct}"
                for ct in adata_ref.uns["mod"]["factor_names"]
            ]
        ].copy()
    else:
        inf_aver = adata_ref.var[
            [
                f"means_per_cluster_mu_fg_{ct}"
                for ct in adata_ref.uns["mod"]["factor_names"]
            ]
        ].copy()
    inf_aver.columns = adata_ref.uns["mod"]["factor_names"]
    return inf_aver


def _map_to_spatial(adata_sp, inf_aver, batch_key, sp_epochs):
    """Train Cell2location on the spatial data and return the abundance DataFrame."""
    # Restrict both matrices to their shared gene set.
    shared = [g for g in adata_sp.var_names if g in set(inf_aver.index)]
    if not shared:
        raise ValueError("Reference and spatial data have no shared genes.")
    adata_sp = adata_sp[:, shared].copy()
    inf_aver = inf_aver.loc[shared, :]

    cell2location.models.Cell2location.setup_anndata(
        adata_sp, batch_key=batch_key if batch_key else None
    )
    mod_sp = cell2location.models.Cell2location(
        adata_sp,
        cell_state_df=inf_aver,
        N_cells_per_location=30,
        detection_alpha=20,
    )
    mod_sp.train(max_epochs=sp_epochs)
    adata_sp = mod_sp.export_posterior(
        adata_sp,
        sample_kwargs={"num_samples": 1000, "batch_size": min(2500, mod_sp.adata.n_obs)},
    )
    return adata_sp


@register_mcp_tool(
    tool_type_name="run_cell2location_deconvolution",
    config={
        "description": (
            "Deconvolve spatial transcriptomics data (e.g. 10x Visium) into "
            "per-location cell-type abundances with cell2location, a Bayesian "
            "model (Kleshchevnikov 2022). Step 1 estimates reference cell-type "
            "signatures from an annotated single-cell/single-nucleus reference "
            "(.h5ad); step 2 maps them onto the spatial data (.h5ad). Returns a "
            "summary of mean cell-type abundance across spots. GPU-recommended; "
            "epochs default LOW for CPU feasibility."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "sc_path": {
                    "type": "string",
                    "description": "An annotated reference .h5ad file of raw counts inside the provider-configured data directory.",
                },
                "sp_path": {
                    "type": "string",
                    "description": "A spatial .h5ad file of raw counts inside the provider-configured data directory (e.g. 10x Visium).",
                },
                "cluster_label": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 128,
                    "description": "obs column in the reference giving the cell-type label to build signatures for (e.g. 'cell_type').",
                },
                "batch_key": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 128,
                    "description": "obs column naming the batch/sample (optional; empty = no batch term). Applied to both reference and spatial setup.",
                },
                "ref_epochs": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5000,
                    "description": "Reference RegressionModel training epochs (default 250; raise on GPU, e.g. 250-1000).",
                },
                "sp_epochs": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5000,
                    "description": "Spatial Cell2location training epochs (default 250; raise on GPU, e.g. 250-30000).",
                },
            },
            "required": ["sc_path", "sp_path", "cluster_label"],
        },
    },
    mcp_config={
        "server_name": "cell2location MCP Server",
        "host": "127.0.0.1",
        "port": 8019,
        "transport": "http",
    },
)
class Cell2locationDeconvolutionTool:
    """Two-step cell2location deconvolution of spatial transcriptomics data."""

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
            batch_key = bounded_text(arguments.get("batch_key"), "batch_key")
            ref_epochs = bounded_integer(
                arguments.get("ref_epochs"),
                "ref_epochs",
                default=250,
                minimum=1,
                maximum=5_000,
            )
            sp_epochs = bounded_integer(
                arguments.get("sp_epochs"),
                "sp_epochs",
                default=250,
                minimum=1,
                maximum=5_000,
            )
        except ValueError as exc:
            return {"error": str(exc)}

        try:
            adata_ref = load_remote_h5ad(sc_path, sc.read_h5ad)
            if cluster_label not in adata_ref.obs:
                return {"error": "cluster_label was not found in reference obs."}
            adata_sp = load_remote_h5ad(sp_path, sc.read_h5ad)
            if batch_key and (
                batch_key not in adata_ref.obs or batch_key not in adata_sp.obs
            ):
                return {"error": "batch_key must exist in both input datasets."}
            reference_types = adata_ref.obs[cluster_label].astype(str).unique().tolist()
            if not 1 <= len(reference_types) <= _MAX_CELL_TYPES:
                return {"error": "cluster_label contains too many cell types."}
            if any(not label or len(label) > 128 for label in reference_types):
                return {"error": "cluster_label contains an invalid cell-type label."}

            inf_aver = _estimate_reference_signatures(
                adata_ref, cluster_label, batch_key, ref_epochs
            )
            adata_sp = _map_to_spatial(adata_sp, inf_aver, batch_key, sp_epochs)

            abundance = adata_sp.obsm["q05_cell_abundance_w_sf"]
            # cell2location names the columns `q05cell_abundance_w_sf_<ct>` (note: no
            # underscore after `q05`), so split on the stable `_w_sf_` suffix to
            # recover the cell type robustly rather than stripping a fixed prefix.
            cell_types = [c.split("_w_sf_")[-1] for c in abundance.columns]
            means = np.asarray(abundance.mean(axis=0)).ravel()
            if (
                abundance.shape[0] != adata_sp.n_obs
                or abundance.shape[1] != len(cell_types)
                or not 1 <= len(cell_types) <= _MAX_CELL_TYPES
                or any(not cell_type or len(cell_type) > 128 for cell_type in cell_types)
                or not np.isfinite(means).all()
                or (means < 0).any()
            ):
                return {"error": "cell2location returned invalid abundance output."}
            mean_abundance = {
                ct: round(float(m), 6) for ct, m in zip(cell_types, means)
            }
            return {
                "n_spots": int(abundance.shape[0]),
                "cell_types": cell_types,
                "mean_abundance": mean_abundance,
                "note": (
                    "Per-spot abundances are q05 (5% posterior quantile) of "
                    "cell_abundance_w_sf. mean_abundance is averaged over all spots. "
                    f"ref_epochs={ref_epochs}, sp_epochs={sp_epochs} (low defaults for "
                    "CPU; raise on GPU for production-quality posteriors)."
                ),
            }
        except Exception as exc:  # never raise out of run()
            return {"error": "cell2location deconvolution failed on the provider."}


if __name__ == "__main__":
    start_mcp_server()
