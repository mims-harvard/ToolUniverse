"""
Milo single-cell differential abundance testing — MCP Server.

Milo (Dann et al., Nature Biotechnology 2022) tests for differential abundance
of cell states between experimental conditions on a k-nearest-neighbour (kNN)
graph. Instead of relying on discrete clusters, it assigns cells to overlapping
*neighbourhoods*, counts how many cells from each biological sample fall into
each neighbourhood, and fits a negative-binomial GLM (edgeR/pyDESeq2 style) to
test each neighbourhood for a shift in abundance across a condition — reporting
a log-fold-change and a spatially-corrected FDR (SpatialFDR) per neighbourhood.

This module exposes Milo as a ToolUniverse *remote* tool because it carries a
heavy single-cell dependency stack (`pertpy` -> scanpy/anndata + mudata +
pyDESeq2/edgeR). Running it on a dedicated server keeps the core ToolUniverse
install light.

Inputs are referenced by an ``adata_path`` (a server-accessible ``.h5ad``)
rather than inlined, because single-cell matrices are large.

One operation is served:
  * run_milo_differential_abundance -> per-neighbourhood differential abundance

The current Milo implementation ships inside `pertpy` as ``pt.tl.Milo`` (the
standalone ``milopy`` package is the legacy reference). This module prefers
pertpy and falls back to milopy if pertpy is unavailable.

References
----------
Dann E, Henderson NC, Teichmann SA, Morgan MD, Marioni JC. "Differential
abundance testing on single-cell data using k-nearest neighbor graphs."
Nature Biotechnology 40, 245-253 (2022).
"""

import re
from typing import Any, Dict

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server
from tooluniverse.remote_argument_validation import (
    bounded_integer,
    bounded_number,
    bounded_text,
    require_argument_object,
)
from tooluniverse.remote_data_path import load_remote_h5ad


_FORMULA_COLUMN_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")


@register_mcp_tool(
    tool_type_name="run_milo_differential_abundance",
    config={
        "description": (
            "Test single-cell differential abundance with Milo (Dann et al., "
            "Nature Biotechnology 2022). Builds a kNN graph, assigns cells to "
            "overlapping neighbourhoods, counts cells per neighbourhood per "
            "biological sample, and fits a negative-binomial GLM to test each "
            "neighbourhood for a shift in abundance across a condition. Returns "
            "the number of neighbourhoods, how many are significant at "
            "SpatialFDR<0.1, and how many of those are enriched (logFC>0) vs "
            "depleted (logFC<0). Input is a server-accessible .h5ad."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "adata_path": {
                    "type": "string",
                    "description": "An .h5ad file of single cells inside the provider-configured data directory.",
                },
                "sample_col": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 64,
                    "pattern": "^[A-Za-z_][A-Za-z0-9_]{0,63}$",
                    "description": "obs column identifying the biological replicate/sample id (the unit of replication).",
                },
                "condition_col": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 64,
                    "pattern": "^[A-Za-z_][A-Za-z0-9_]{0,63}$",
                    "description": "obs column naming the condition being tested for differential abundance (design '~condition_col').",
                },
                "n_pcs": {
                    "type": "integer",
                    "minimum": 2,
                    "maximum": 100,
                    "description": "Number of principal components for the kNN graph (default 30).",
                },
                "n_neighbors": {
                    "type": "integer",
                    "minimum": 2,
                    "maximum": 200,
                    "description": "Number of neighbours for the kNN graph (default 15).",
                },
                "prop": {
                    "type": "number",
                    "exclusiveMinimum": 0,
                    "maximum": 1,
                    "description": "Fraction of cells sampled as neighbourhood index cells (default 0.1).",
                },
                "spatial_fdr": {
                    "type": "number",
                    "exclusiveMinimum": 0,
                    "maximum": 1,
                    "description": "SpatialFDR threshold for calling a neighbourhood significant (default 0.1).",
                },
            },
            "required": ["adata_path", "sample_col", "condition_col"],
        },
    },
    mcp_config={
        "server_name": "Milo MCP Server",
        "host": "127.0.0.1",
        "port": 8023,
        "transport": "http",
    },
)
class MiloDifferentialAbundanceTool:
    """Run Milo differential abundance testing on kNN-graph neighbourhoods."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            arguments = require_argument_object(arguments)
        except ValueError as exc:
            return {"error": str(exc)}
        adata_path = arguments.get("adata_path")
        sample_col = arguments.get("sample_col")
        condition_col = arguments.get("condition_col")
        if not (adata_path and sample_col and condition_col):
            return {
                "error": "Missing required parameter(s): adata_path, sample_col, condition_col"
            }

        try:
            sample_col = bounded_text(sample_col, "sample_col", maximum=64)
            condition_col = bounded_text(
                condition_col, "condition_col", maximum=64
            )
            if not _FORMULA_COLUMN_PATTERN.fullmatch(sample_col) or not _FORMULA_COLUMN_PATTERN.fullmatch(condition_col):
                raise ValueError(
                    "sample_col and condition_col must use letters, digits, and underscores only."
                )
            if sample_col == condition_col:
                raise ValueError("sample_col and condition_col must be different.")
            n_pcs = bounded_integer(
                arguments.get("n_pcs"),
                "n_pcs",
                default=30,
                minimum=2,
                maximum=100,
            )
            n_neighbors = bounded_integer(
                arguments.get("n_neighbors"),
                "n_neighbors",
                default=15,
                minimum=2,
                maximum=200,
            )
            prop = bounded_number(
                arguments.get("prop"),
                "prop",
                default=0.1,
                minimum=0,
                maximum=1,
                exclusive_minimum=True,
            )
            spatial_fdr = bounded_number(
                arguments.get("spatial_fdr"),
                "spatial_fdr",
                default=0.1,
                minimum=0,
                maximum=1,
                exclusive_minimum=True,
            )
        except ValueError as exc:
            return {"error": str(exc)}

        try:
            import scanpy as sc
        except ImportError as exc:
            return {"error": "scanpy is not installed on the provider."}

        # Prefer pertpy (current Milo implementation); fall back to milopy.
        backend = None
        milo = None
        try:
            import pertpy as pt

            milo = pt.tl.Milo()
            backend = "pertpy"
        except ImportError:
            try:
                import milopy
                import milopy.core as milo_core  # noqa: F401

                backend = "milopy"
            except ImportError:
                return {
                    "error": (
                        "Neither 'pertpy' nor 'milopy' is installed on the provider. "
                        "Install pertpy to run Milo."
                    )
                }

        try:
            adata = load_remote_h5ad(adata_path, sc.read_h5ad)
        except Exception as exc:  # noqa: BLE001
            return {"error": f"Invalid adata_path: {exc}"}

        for col in (sample_col, condition_col):
            if col not in adata.obs.columns:
                return {"error": f"Column '{col}' was not found in adata.obs."}
        if adata.n_obs < 3 or n_neighbors >= adata.n_obs:
            return {"error": "n_neighbors must be smaller than the number of cells."}
        if adata.obs[condition_col].astype(str).nunique() < 2:
            return {"error": "condition_col must contain at least two conditions."}

        try:
            if backend == "pertpy":
                return self._run_pertpy(
                    sc,
                    milo,
                    adata,
                    sample_col,
                    condition_col,
                    n_pcs,
                    n_neighbors,
                    prop,
                    spatial_fdr,
                )
            return self._run_milopy(
                sc,
                milo_core,
                adata,
                sample_col,
                condition_col,
                n_pcs,
                n_neighbors,
                prop,
                spatial_fdr,
            )
        except Exception as exc:  # noqa: BLE001
            return {"error": "Milo differential abundance testing failed on the provider."}

    @staticmethod
    def _build_graph(sc, adata, n_pcs, n_neighbors):
        """Compute PCA + a kNN graph in place (Milo reads .obsp connectivities)."""
        if "X_pca" not in adata.obsm:
            sc.pp.pca(
                adata,
                n_comps=min(n_pcs, max(1, adata.n_vars - 1), adata.n_obs - 1),
            )
        # never request more PCs than X_pca actually has (a pre-computed X_pca
        # may have fewer components than the requested n_pcs).
        n_pcs = min(n_pcs, adata.obsm["X_pca"].shape[1])
        sc.pp.neighbors(adata, n_neighbors=n_neighbors, n_pcs=n_pcs)

    @staticmethod
    def _summarize(logfc, spatial_fdr_vals, threshold):
        """Turn per-neighbourhood logFC / SpatialFDR into a bounded summary dict."""
        n_neighbourhoods = int(len(logfc))
        significant = [
            (lfc, fdr)
            for lfc, fdr in zip(logfc, spatial_fdr_vals)
            if fdr is not None and fdr == fdr and fdr < threshold  # fdr==fdr drops NaN
        ]
        n_significant = len(significant)
        n_da_up = sum(1 for lfc, _ in significant if lfc is not None and lfc > 0)
        n_da_down = sum(1 for lfc, _ in significant if lfc is not None and lfc < 0)
        return n_neighbourhoods, n_significant, n_da_up, n_da_down

    def _run_pertpy(
        self,
        sc,
        milo,
        adata,
        sample_col,
        condition_col,
        n_pcs,
        n_neighbors,
        prop,
        spatial_fdr,
    ):
        mdata = milo.load(adata)
        rna = mdata["rna"]
        self._build_graph(sc, rna, n_pcs, n_neighbors)
        milo.make_nhoods(rna, prop=prop)
        mdata = milo.count_nhoods(mdata, sample_col=sample_col)
        milo.da_nhoods(mdata, design="~" + condition_col)

        nhood_var = mdata["milo"].var
        logfc = nhood_var["logFC"].tolist()
        fdr_vals = nhood_var["SpatialFDR"].tolist()
        n_neighbourhoods, n_significant, n_da_up, n_da_down = self._summarize(
            logfc, fdr_vals, spatial_fdr
        )
        return {
            "backend": "pertpy",
            "sample_col": sample_col,
            "condition_col": condition_col,
            "design": "~" + condition_col,
            "spatial_fdr_threshold": spatial_fdr,
            "n_neighbourhoods": n_neighbourhoods,
            "n_significant": n_significant,
            "n_da_up": n_da_up,
            "n_da_down": n_da_down,
            "note": (
                f"{n_significant}/{n_neighbourhoods} neighbourhoods are "
                f"differentially abundant at SpatialFDR<{spatial_fdr} "
                f"({n_da_up} enriched, {n_da_down} depleted) for '{condition_col}'."
            ),
        }

    def _run_milopy(
        self,
        sc,
        milo_core,
        adata,
        sample_col,
        condition_col,
        n_pcs,
        n_neighbors,
        prop,
        spatial_fdr,
    ):
        self._build_graph(sc, adata, n_pcs, n_neighbors)
        milo_core.make_nhoods(adata, prop=prop)
        milo_core.count_nhoods(adata, sample_col=sample_col)
        milo_core.DA_nhoods(adata, design="~" + condition_col)

        nhood_var = adata.uns["nhood_adata"].obs
        logfc = nhood_var["logFC"].tolist()
        fdr_vals = nhood_var["SpatialFDR"].tolist()
        n_neighbourhoods, n_significant, n_da_up, n_da_down = self._summarize(
            logfc, fdr_vals, spatial_fdr
        )
        return {
            "backend": "milopy",
            "sample_col": sample_col,
            "condition_col": condition_col,
            "design": "~" + condition_col,
            "spatial_fdr_threshold": spatial_fdr,
            "n_neighbourhoods": n_neighbourhoods,
            "n_significant": n_significant,
            "n_da_up": n_da_up,
            "n_da_down": n_da_down,
            "note": (
                f"{n_significant}/{n_neighbourhoods} neighbourhoods are "
                f"differentially abundant at SpatialFDR<{spatial_fdr} "
                f"({n_da_up} enriched, {n_da_down} depleted) for '{condition_col}'."
            ),
        }


if __name__ == "__main__":
    start_mcp_server()
