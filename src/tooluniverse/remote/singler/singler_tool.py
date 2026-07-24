"""
SingleR automated cell-type annotation — MCP Server.

SingleR (Aran et al., Nature Immunology 2019) annotates single cells by
correlating each cell's expression against a labeled reference transcriptome and
assigning the best-matching label — the standard reference-based alternative to
manual marker-gene annotation of clusters. It works per cell (not per cluster)
and reports a fine-grained label for every cell.

Served as a ToolUniverse *remote* tool because the engine is R/Bioconductor
(`SingleR` + `celldex` for the built-in references). The Python side reads the
query ``.h5ad`` with scanpy and hands the expression matrix to a bundled R
script (MatrixMarket interchange — no zellkonverter/basilisk needed); the script
runs ``SingleR::SingleR`` and returns the per-cell labels as JSON.

Two reference modes:
  * **built-in** — a celldex reference by name (e.g. ``HumanPrimaryCellAtlasData``,
    ``BlueprintEncodeData``, ``MonacoImmuneData``), downloaded on the server.
  * **bring-your-own** — a labeled reference ``.h5ad`` (``ref_adata_path`` +
    ``ref_labels_key``), for annotating against a custom atlas.

Supply log-normalized expression for both query and reference (SingleR's
default assumption).

Reference
---------
Aran D, Looney AP, Liu L, et al. "Reference-based analysis of lung single-cell
sequencing reveals a transitional profibrotic macrophage." Nature Immunology 20,
163-172 (2019).
"""

import json
import os
import subprocess
import tempfile
from collections import Counter
from typing import Any, Dict, List

import scanpy as sc
from scipy.io import mmwrite
from scipy.sparse import csr_matrix

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server

_R_SCRIPT = os.path.join(os.path.dirname(__file__), "singler_annotate.R")
_RSCRIPT = os.environ.get("RSCRIPT_BIN", "Rscript")
_TIMEOUT = 1800
_MAX_PERCELL_LABELS = 50000

# celldex built-in references (allow-list; names are celldex function names).
_CELLDEX_REFS = {
    "HumanPrimaryCellAtlasData",
    "BlueprintEncodeData",
    "MonacoImmuneData",
    "DatabaseImmuneCellExpressionData",
    "NovershternHematopoieticData",
    "ImmGenData",
    "MouseRNAseqData",
}


def _export_matrix(adata, work: str, prefix: str) -> None:
    """Write adata (cells x genes) as a genes x cells MatrixMarket file + gene names."""
    genes_by_cells = csr_matrix(adata.X).T  # SingleR wants features x samples
    mmwrite(os.path.join(work, f"{prefix}.mtx"), genes_by_cells)
    with open(os.path.join(work, f"{prefix}_genes.txt"), "w") as fh:
        fh.write("\n".join(str(g) for g in adata.var_names))


def _run_rscript(work: str) -> Dict[str, Any]:
    """Run the bundled SingleR R script over a prepared work dir; return parsed JSON."""
    if not os.path.exists(_R_SCRIPT):
        return {"error": f"SingleR R script not found at {_R_SCRIPT}."}
    try:
        proc = subprocess.run(
            [_RSCRIPT, _R_SCRIPT, work],
            capture_output=True,
            text=True,
            timeout=_TIMEOUT,
        )
    except FileNotFoundError:
        return {
            "error": f"Rscript not found ('{_RSCRIPT}'); install R + SingleR/celldex."
        }
    except subprocess.TimeoutExpired:
        return {"error": f"SingleR timed out after {_TIMEOUT}s."}
    out_path = os.path.join(work, "output.json")
    if proc.returncode != 0 or not os.path.exists(out_path):
        return {
            "error": f"SingleR (R) failed: {proc.stderr[-600:] or proc.stdout[-600:]}"
        }
    with open(out_path) as fh:
        return json.load(fh)


def _summarize(labels: List[str], cell_ids: List[str], ref: str) -> Dict[str, Any]:
    """Shape the per-cell labels into the response envelope (compact for big inputs)."""
    n = len(labels)
    result = {
        "model": "SingleR",
        "reference": ref,
        "n_cells": n,
        "label_counts": dict(Counter(labels).most_common()),
    }
    if n <= _MAX_PERCELL_LABELS:
        result["predicted_labels"] = labels
        result["cell_ids"] = cell_ids
    else:
        result["note"] = (
            f"{n} cells > {_MAX_PERCELL_LABELS}: per-cell labels omitted; see label_counts."
        )
    return result


@register_mcp_tool(
    tool_type_name="run_singler_annotate",
    config={
        "description": (
            "Annotate single cells with SingleR (Aran 2019): correlate each cell "
            "against a labeled reference transcriptome and assign the best-matching "
            "cell-type label, per cell. Reference is either a built-in celldex "
            "panel (e.g. HumanPrimaryCellAtlasData, BlueprintEncodeData, "
            "MonacoImmuneData) or your own labeled .h5ad (ref_adata_path + "
            "ref_labels_key). Returns a label for every cell plus label counts. "
            "Supply log-normalized expression."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "adata_path": {
                    "type": "string",
                    "description": "Server-accessible path to the query .h5ad (log-normalized expression in .X).",
                },
                "celldex_ref": {
                    "type": "string",
                    "description": "Built-in reference name (one of HumanPrimaryCellAtlasData, BlueprintEncodeData, MonacoImmuneData, DatabaseImmuneCellExpressionData, NovershternHematopoieticData, ImmGenData, MouseRNAseqData). Omit when using a bring-your-own reference.",
                },
                "ref_label_field": {
                    "type": "string",
                    "description": "celldex label granularity: 'label.main' (default) or 'label.fine'.",
                },
                "ref_adata_path": {
                    "type": "string",
                    "description": "Bring-your-own reference .h5ad (log-normalized); used when celldex_ref is omitted.",
                },
                "ref_labels_key": {
                    "type": "string",
                    "description": "obs column in ref_adata_path holding the reference cell-type labels.",
                },
            },
            "required": ["adata_path"],
        },
    },
    mcp_config={
        "server_name": "SingleR Annotation MCP Server",
        "host": "127.0.0.1",
        "port": 8029,
        "transport": "http",
    },
)
class SinglerAnnotateTool:
    """Annotate single cells against a labeled reference with SingleR."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        adata_path = arguments.get("adata_path")
        if not adata_path:
            return {"error": "Missing required parameter: adata_path"}
        celldex_ref = arguments.get("celldex_ref") or None
        ref_adata_path = arguments.get("ref_adata_path") or None
        ref_labels_key = arguments.get("ref_labels_key") or None

        if celldex_ref and celldex_ref not in _CELLDEX_REFS:
            return {
                "error": f"celldex_ref must be one of {sorted(_CELLDEX_REFS)}; got '{celldex_ref}'."
            }
        if not celldex_ref and not (ref_adata_path and ref_labels_key):
            return {
                "error": (
                    "Provide either celldex_ref (a built-in reference) or both "
                    "ref_adata_path and ref_labels_key (a bring-your-own reference)."
                )
            }

        adata = sc.read_h5ad(adata_path)
        with tempfile.TemporaryDirectory() as work:
            _export_matrix(adata, work, "query")
            config = {
                "celldex_ref": celldex_ref or "",
                "ref_label_field": arguments.get("ref_label_field") or "label.main",
            }
            if not celldex_ref:
                ref = sc.read_h5ad(ref_adata_path)
                if ref_labels_key not in ref.obs:
                    return {
                        "error": f"ref_labels_key '{ref_labels_key}' not in reference obs."
                    }
                _export_matrix(ref, work, "ref")
                with open(os.path.join(work, "ref_labels.txt"), "w") as fh:
                    fh.write("\n".join(ref.obs[ref_labels_key].astype(str)))
            with open(os.path.join(work, "config.json"), "w") as fh:
                json.dump(config, fh)

            res = _run_rscript(work)
        if "error" in res:
            return res
        cell_ids = adata.obs_names.astype(str).tolist()
        return _summarize(
            res["predicted_labels"], cell_ids, res.get("ref", "reference")
        )


if __name__ == "__main__":
    start_mcp_server()
