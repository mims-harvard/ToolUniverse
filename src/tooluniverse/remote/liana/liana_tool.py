"""
LIANA cell-cell communication inference — MCP Server.

LIANA (LIgand-receptor ANalysis frAmework; Dimitrov et al., Nature
Communications 2022) is a consensus framework for inferring cell-cell
communication from single-cell transcriptomics. It re-implements and unifies
the scoring functions of established methods — CellPhoneDB, CellChat, NATMI,
Connectome, SingleCellSignalR, logFC, geometric-mean — over a shared set of
curated ligand-receptor resources, so results from different methods are
directly comparable.

This module exposes LIANA as a ToolUniverse *remote* tool because it carries a
heavy single-cell dependency stack (`liana` -> scanpy/anndata + scikit-learn +
the bundled ligand-receptor resources). Running it on a dedicated server keeps
the core ToolUniverse install light.

Inputs are referenced by an ``adata_path`` (a server-accessible ``.h5ad`` of
log1p-normalized expression) rather than inlined, because single-cell matrices
are large.

One operation is served:
  * run_liana_cellphonedb -> top ligand-receptor interactions between cell
    types via the CellPhoneDB permutation-test method, scored by magnitude
    (`lr_means`) and specificity (`cellphone_pvals`).

References
----------
Dimitrov D, Türei D, Garrido-Rodriguez M, et al. "Comparison of methods and
resources for cell-cell communication inference from single-cell RNA-Seq data."
Nature Communications 13, 3224 (2022).
"""

from typing import Any, Dict

import scanpy as sc
import liana as li

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server


@register_mcp_tool(
    tool_type_name="run_liana_cellphonedb",
    config={
        "description": (
            "Infer cell-cell communication from a single-cell RNA-seq dataset "
            "using LIANA's CellPhoneDB method, and return the top ligand-receptor "
            "interactions between cell types. Expects an .h5ad of log1p-normalized "
            "expression with a cell-type label column in obs. Each interaction is "
            "scored by magnitude (lr_means) and specificity (cellphone_pvals)."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "adata_path": {
                    "type": "string",
                    "description": "Server-accessible path or URL to an .h5ad AnnData of LOG1P-NORMALIZED expression.",
                },
                "cluster_key": {
                    "type": "string",
                    "description": "obs column holding the cell-type / cluster labels to compute interactions between.",
                },
                "top_n": {
                    "type": "integer",
                    "description": "Number of top interactions to return, ranked by specificity then magnitude (default 50).",
                },
                "expr_prop": {
                    "type": "number",
                    "description": "Minimum fraction of cells in a group expressing a gene for it to be considered (default 0.1).",
                },
            },
            "required": ["adata_path", "cluster_key"],
        },
    },
    mcp_config={
        "server_name": "LIANA MCP Server",
        "host": "127.0.0.1",
        "port": 8017,
        "transport": "http",
    },
)
class LianaCellPhoneDBTool:
    """Run LIANA's CellPhoneDB method and return top ligand-receptor interactions."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        adata_path = arguments.get("adata_path")
        cluster_key = arguments.get("cluster_key")
        if not (adata_path and cluster_key):
            return {"error": "Missing required parameter(s): adata_path, cluster_key"}
        top_n = arguments.get("top_n")
        top_n = 50 if top_n is None else int(top_n)
        expr_prop = arguments.get("expr_prop")
        expr_prop = 0.1 if expr_prop is None else float(expr_prop)

        try:
            adata = sc.read_h5ad(adata_path)
        except Exception as exc:  # noqa: BLE001
            return {"error": f"Failed to load AnnData from {adata_path}: {exc}"}

        if cluster_key not in adata.obs.columns:
            return {
                "error": (
                    f"cluster_key '{cluster_key}' not found in adata.obs. "
                    f"Available columns: {list(adata.obs.columns)}"
                )
            }

        try:
            li.mt.cellphonedb(
                adata,
                groupby=cluster_key,
                expr_prop=expr_prop,
                use_raw=False,
                verbose=False,
            )
        except Exception as exc:  # noqa: BLE001
            return {"error": f"LIANA CellPhoneDB run failed: {exc}"}

        res = adata.uns.get("liana_res")
        if res is None or len(res) == 0:
            return {
                "error": "LIANA produced no interactions (empty liana_res); "
                "check that the matrix is log1p-normalized and the cluster_key is correct."
            }

        # Lower cellphone_pvals = more specific; higher lr_means = stronger magnitude.
        sort_cols = [c for c in ("cellphone_pvals", "lr_means") if c in res.columns]
        ascending = [True, False][: len(sort_cols)]
        if sort_cols:
            res = res.sort_values(sort_cols, ascending=ascending)
        res = res.head(top_n)

        keep = [
            c
            for c in (
                "source",
                "target",
                "ligand_complex",
                "receptor_complex",
                "lr_means",
                "cellphone_pvals",
            )
            if c in res.columns
        ]
        records = (
            res[keep].to_dict(orient="records")
            if keep
            else res.to_dict(orient="records")
        )

        return {
            "method": "LIANA-CellPhoneDB",
            "cluster_key": cluster_key,
            "n_interactions": int(len(records)),
            "interactions": records,
        }


if __name__ == "__main__":
    start_mcp_server()
