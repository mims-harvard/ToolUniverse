"""
DestVI spatial-transcriptomics deconvolution — MCP Server.

DestVI (Deconvolution of Spatial Transcriptomics profiles using Variational
Inference; Lopez et al., Nature Biotechnology 2022; part of the scvi-tools
platform, Gayoso et al., Nature Biotechnology 2022) estimates, for every spot
of a spatial transcriptomics slide, the proportion of each cell type present.
It is a multi-resolution deconvolution method that also recovers continuous
within-cell-type variation.

DestVI is a *two-step* model:
  1. A ``CondSCVI`` model is trained on an annotated single-cell RNA-seq
     reference (cells labelled by cell type) to learn per-cell-type expression
     profiles.
  2. A ``DestVI`` model is built ``from_rna_model`` and trained on the spatial
     data; ``get_proportions()`` then returns a spots x cell_types DataFrame of
     deconvolved proportions.

This module exposes DestVI as a ToolUniverse *remote* tool because it carries a
heavy deep-learning dependency stack (`scvi-tools` -> PyTorch + Lightning +
Pyro + scanpy/anndata). Running it on a dedicated server keeps the core
ToolUniverse install light; the model trains on CPU for small datasets and on
GPU for large ones.

Inputs are referenced by file paths (server-accessible ``.h5ad`` files) rather
than inlined, because single-cell and spatial matrices are large.

References
----------
Lopez R, Li B, Keren-Shaul H, et al. "DestVI identifies continuums of cell
types in spatial transcriptomics data." Nature Biotechnology 40, 1360-1369
(2022).
Gayoso A, Lopez R, Xing G, et al. "A Python library for probabilistic analysis
of single-cell omics data." Nature Biotechnology 40, 163-166 (2022).
"""

from typing import Any, Dict

import scanpy as sc
from scvi.model import CondSCVI, DestVI

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server


@register_mcp_tool(
    tool_type_name="run_destvi_deconvolution",
    config={
        "description": (
            "Deconvolve a spatial transcriptomics slide with DestVI: train a "
            "CondSCVI model on an annotated single-cell RNA-seq reference, then "
            "fit DestVI on the spatial data to estimate, per spot, the "
            "proportion of each cell type. Returns per-cell-type mean "
            "proportions across spots. Inputs are server-accessible .h5ad files."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "sc_path": {
                    "type": "string",
                    "description": "Server-accessible path or URL to the single-cell reference .h5ad of RAW counts, annotated with `cluster_label` in obs.",
                },
                "sp_path": {
                    "type": "string",
                    "description": "Server-accessible path or URL to the spatial transcriptomics .h5ad of RAW counts (spots x genes).",
                },
                "cluster_label": {
                    "type": "string",
                    "description": "obs column in the single-cell reference naming the cell-type label used as deconvolution targets (e.g. 'cell_type').",
                },
                "sc_epochs": {
                    "type": "integer",
                    "description": "Training epochs for the CondSCVI reference model (default 100, the scvi-tools default).",
                },
                "st_epochs": {
                    "type": "integer",
                    "description": "Training epochs for the DestVI spatial model (default 500, the scvi-tools default).",
                },
            },
            "required": ["sc_path", "sp_path", "cluster_label"],
        },
    },
    mcp_config={
        "server_name": "DestVI MCP Server",
        "host": "127.0.0.1",
        "port": 8020,
        "transport": "http",
    },
)
class DestviDeconvolutionTool:
    """Train CondSCVI + DestVI and return per-cell-type spatial proportions."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        sc_path = arguments.get("sc_path")
        sp_path = arguments.get("sp_path")
        cluster_label = arguments.get("cluster_label")
        if not (sc_path and sp_path and cluster_label):
            return {
                "error": "Missing required parameter(s): sc_path, sp_path, cluster_label"
            }
        sc_epochs = arguments.get("sc_epochs")
        sc_epochs = 100 if sc_epochs is None else int(sc_epochs)
        st_epochs = arguments.get("st_epochs")
        st_epochs = 500 if st_epochs is None else int(st_epochs)

        try:
            sc_adata = sc.read_h5ad(sc_path)
            if cluster_label not in sc_adata.obs:
                return {
                    "error": f"cluster_label '{cluster_label}' not found in single-cell obs columns."
                }
            st_adata = sc.read_h5ad(sp_path)

            # Step 1: train CondSCVI on the annotated single-cell reference.
            CondSCVI.setup_anndata(sc_adata, labels_key=cluster_label)
            sc_model = CondSCVI(sc_adata)
            sc_model.train(max_epochs=sc_epochs)

            # Step 2: build DestVI from the reference model and fit on spatial data.
            DestVI.setup_anndata(st_adata)
            st_model = DestVI.from_rna_model(st_adata, sc_model)
            st_model.train(max_epochs=st_epochs)
            props = st_model.get_proportions()  # spots x cell_types DataFrame

            cell_types = [str(c) for c in props.columns]
            mean_proportions = {
                str(ct): float(props[ct].mean()) for ct in props.columns
            }
            return {
                "model": "DestVI",
                "n_spots": int(props.shape[0]),
                "cell_types": cell_types,
                "mean_proportions": mean_proportions,
                "note": (
                    "Per-cell-type mean of DestVI-estimated proportions across all "
                    "spots; each spot's proportions sum to ~1."
                ),
            }
        except Exception as exc:  # never raise out of run()
            return {"error": f"DestVI deconvolution failed: {exc}"}


if __name__ == "__main__":
    start_mcp_server()
