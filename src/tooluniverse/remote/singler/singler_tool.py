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
import numpy as np
from scipy.io import mmwrite
from scipy.sparse import csr_matrix

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server
from tooluniverse.remote_argument_validation import (
    bounded_text,
    require_argument_object,
)
from tooluniverse.remote_data_path import load_remote_h5ad

_R_SCRIPT = os.path.join(os.path.dirname(__file__), "singler_annotate.R")
_RSCRIPT = os.environ.get("RSCRIPT_BIN", "Rscript")
_TIMEOUT = 1800
_MAX_PERCELL_LABELS = 50000
_MAX_OUTPUT_BYTES = 10_000_000
_MAX_LABELS = 256

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
    values = (
        adata.X.data
        if hasattr(adata.X, "nnz") and hasattr(adata.X, "data")
        else np.asarray(adata.X)
    )
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("SingleR expression values must be finite and non-negative")
    gene_ids = [str(gene) for gene in adata.var_names]
    if len(set(gene_ids)) != len(gene_ids) or any(
        not gene or len(gene) > 256 or "\n" in gene or "\r" in gene
        for gene in gene_ids
    ):
        raise ValueError("SingleR requires unique, bounded gene identifiers")
    genes_by_cells = csr_matrix(adata.X).T  # SingleR wants features x samples
    mmwrite(os.path.join(work, f"{prefix}.mtx"), genes_by_cells)
    with open(os.path.join(work, f"{prefix}_genes.txt"), "w") as fh:
        fh.write("\n".join(gene_ids))


def _run_rscript(work: str) -> Dict[str, Any]:
    """Run the bundled SingleR R script over a prepared work dir; return parsed JSON."""
    if not os.path.exists(_R_SCRIPT):
        return {"error": "The provider's bundled SingleR script is unavailable."}
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
        return {"error": f"SingleR timed out after {_TIMEOUT}s."}
    except OSError:
        return {"error": "The provider could not start SingleR."}
    out_path = os.path.join(work, "output.json")
    if proc.returncode != 0 or not os.path.exists(out_path):
        return {"error": f"SingleR failed on the provider (returncode {proc.returncode})."}
    if os.path.getsize(out_path) > _MAX_OUTPUT_BYTES:
        return {"error": "SingleR output exceeded the provider response limit."}
    try:
        with open(out_path, encoding="utf-8") as fh:
            result = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {"error": "SingleR produced an invalid provider result."}
    return result if isinstance(result, dict) else {"error": "SingleR produced an invalid provider result."}


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
                    "description": "A query .h5ad file inside the provider-configured data directory (log-normalized expression in .X).",
                },
                "celldex_ref": {
                    "type": "string",
                    "enum": sorted(_CELLDEX_REFS),
                    "description": "Built-in reference name (one of HumanPrimaryCellAtlasData, BlueprintEncodeData, MonacoImmuneData, DatabaseImmuneCellExpressionData, NovershternHematopoieticData, ImmGenData, MouseRNAseqData). Omit when using a bring-your-own reference.",
                },
                "ref_label_field": {
                    "type": "string",
                    "enum": ["label.main", "label.fine"],
                    "description": "celldex label granularity: 'label.main' (default) or 'label.fine'.",
                },
                "ref_adata_path": {
                    "type": "string",
                    "description": "A bring-your-own reference .h5ad file inside the provider-configured data directory; used when celldex_ref is omitted.",
                },
                "ref_labels_key": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 128,
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
        try:
            arguments = require_argument_object(arguments)
        except ValueError as exc:
            return {"error": str(exc)}
        adata_path = arguments.get("adata_path")
        if not adata_path:
            return {"error": "Missing required parameter: adata_path"}
        ref_adata_path = arguments.get("ref_adata_path") or None
        try:
            celldex_ref = bounded_text(
                arguments.get("celldex_ref"),
                "celldex_ref",
                maximum=40,
                allowed=_CELLDEX_REFS,
            )
            ref_labels_key = bounded_text(
                arguments.get("ref_labels_key"), "ref_labels_key"
            )
            ref_label_field = bounded_text(
                arguments.get("ref_label_field"),
                "ref_label_field",
                default="label.main",
                maximum=10,
                allowed={"label.main", "label.fine"},
            )
        except ValueError as exc:
            return {"error": str(exc)}

        if not celldex_ref and not (ref_adata_path and ref_labels_key):
            return {
                "error": (
                    "Provide either celldex_ref (a built-in reference) or both "
                    "ref_adata_path and ref_labels_key (a bring-your-own reference)."
                )
            }
        if celldex_ref and (ref_adata_path or ref_labels_key):
            return {"error": "Choose either celldex_ref or a custom reference, not both."}

        try:
            adata = load_remote_h5ad(adata_path, sc.read_h5ad)
        except ValueError as exc:
            return {"error": f"Invalid adata_path: {exc}"}
        with tempfile.TemporaryDirectory() as work:
            try:
                _export_matrix(adata, work, "query")
            except ValueError as exc:
                return {"error": str(exc)}
            config = {
                "celldex_ref": celldex_ref or "",
                "ref_label_field": ref_label_field,
            }
            if not celldex_ref:
                try:
                    ref = load_remote_h5ad(ref_adata_path, sc.read_h5ad)
                except ValueError as exc:
                    return {"error": f"Invalid ref_adata_path: {exc}"}
                if ref_labels_key not in ref.obs:
                    return {"error": "ref_labels_key was not found in reference obs."}
                ref_labels = ref.obs[ref_labels_key].astype(str).tolist()
                if not 1 <= len(set(ref_labels)) <= _MAX_LABELS or any(
                    not label or len(label) > 128 or "\n" in label or "\r" in label
                    for label in ref_labels
                ):
                    return {"error": "Reference labels are too numerous or invalid."}
                try:
                    _export_matrix(ref, work, "ref")
                except ValueError as exc:
                    return {"error": str(exc)}
                with open(os.path.join(work, "ref_labels.txt"), "w") as fh:
                    fh.write("\n".join(ref_labels))
            with open(os.path.join(work, "config.json"), "w") as fh:
                json.dump(config, fh)

            res = _run_rscript(work)
        if "error" in res:
            return res
        cell_ids = adata.obs_names.astype(str).tolist()
        labels = res.get("predicted_labels")
        if (
            not isinstance(labels, list)
            or len(labels) != adata.n_obs
            or any(not isinstance(label, str) or not label or len(label) > 128 for label in labels)
        ):
            return {"error": "SingleR returned invalid prediction labels."}
        if len(set(labels)) > _MAX_LABELS:
            return {"error": "SingleR returned too many prediction labels."}
        return _summarize(labels, cell_ids, res.get("ref", "reference"))


if __name__ == "__main__":
    start_mcp_server()
