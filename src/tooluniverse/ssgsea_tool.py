"""Single-sample Gene Set Enrichment Analysis (ssGSEA, pure NumPy).

ssGSEA (Barbie et al., Nature 2009) scores, *for each sample independently*, how
enriched a gene set is among that sample's highly-expressed genes — turning an
expression matrix + gene sets into a (gene_set x sample) signature-score matrix.
It is the basis of per-sample signature scoring (immune infiltration, pathway
activity, molecular subtyping). Unlike GSEA-prerank (one ranked contrast), this
takes a full expression matrix and needs no phenotype labels.

For each sample the genes are ranked by expression; for each gene set the score
is the integrated (summed) difference between the rank-weighted cumulative
distribution of set genes and that of the remaining genes — a positive score
means the set's genes sit among the sample's top-expressed genes.

Deterministic rank-based math (no R, no permutation), so it runs and is testable
directly. ``run()`` returns a ``{status, data, metadata}`` dict and never raises.

Reference
---------
Barbie DA, Tamayo P, Boehm JS, et al. "Systematic RNA interference reveals that
oncogenic KRAS-driven cancers require TBK1." Nature 462, 108-112 (2009).
"""

from typing import Any, Dict, List, Optional

import numpy as np

from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("SSGSEATool")
class SSGSEATool(BaseTool):
    """Single-sample GSEA: per-sample enrichment score for each gene set."""

    def __init__(self, tool_config: Optional[Dict[str, Any]] = None):
        super().__init__(tool_config)
        self.tool_config = tool_config or {}

    # ------------------------------------------------------------------ run
    def run(self, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        args = arguments or {}
        parsed = self._parse_expression(args)
        if isinstance(parsed, dict) and "error" in parsed:
            return parsed
        genes, samples, matrix = parsed  # matrix: genes x samples

        gene_sets, gs_error = self._parse_gene_sets(args)
        if gs_error is not None:
            return gs_error

        alpha = float(args.get("alpha") or 0.25)
        index = {g: i for i, g in enumerate(genes)}
        set_idx = {
            name: np.array(sorted({index[g] for g in members if g in index}), dtype=int)
            for name, members in gene_sets.items()
        }

        scores: Dict[str, Dict[str, float]] = {}
        skipped = []
        for name, idx in set_idx.items():
            if len(idx) < 2:
                skipped.append(name)
                continue
            scores[name] = {
                samples[j]: self._ssgsea(matrix[:, j], idx, alpha)
                for j in range(matrix.shape[1])
            }

        if not scores:
            return self._err(
                "No gene set has >= 2 genes present in the expression matrix."
            )
        return {
            "status": "success",
            "data": {
                "n_genes": int(len(genes)),
                "n_samples": int(len(samples)),
                "samples": samples,
                "enrichment_scores": scores,
                "skipped_sets": skipped,
            },
            "metadata": {
                "method": "ssGSEA (Barbie et al. 2009)",
                "alpha": alpha,
                "note": (
                    "enrichment_scores[set][sample]; positive = the set's genes are "
                    "among that sample's highly-expressed genes. Scores are "
                    "comparable across samples for a given set."
                ),
            },
        }

    # --------------------------------------------------------------- ssgsea
    @staticmethod
    def _ssgsea(expr: np.ndarray, set_idx: np.ndarray, alpha: float) -> float:
        """ssGSEA enrichment score for one sample (expr) and one gene set."""
        n = len(expr)
        order = np.argsort(expr)[::-1]  # gene indices, highest expression first
        # rank-based weight magnitude: top-expressed gene gets the largest rank
        rank_w = np.empty(n)
        rank_w[order] = np.arange(n, 0, -1, dtype=float)
        in_set = np.zeros(n, dtype=bool)
        in_set[set_idx] = True
        tag = in_set[order]
        w = (rank_w[order] ** alpha) * tag
        denom = w.sum()
        if denom == 0:
            return 0.0
        p_hit = np.cumsum(w) / denom
        p_miss = np.cumsum((~tag).astype(float)) / (n - tag.sum())
        return float(np.sum(p_hit - p_miss))

    # -------------------------------------------------------------- inputs
    def _parse_expression(self, args: Dict[str, Any]):
        expr = args.get("expression")
        if isinstance(expr, dict) and expr:
            genes = [str(g) for g in expr]
            try:
                rows = [
                    [
                        float(v)
                        for v in (vals if isinstance(vals, (list, tuple)) else [vals])
                    ]
                    for vals in expr.values()
                ]
            except (TypeError, ValueError):
                return self._err("expression values must be numbers (per sample).")
            widths = {len(r) for r in rows}
            if len(widths) != 1:
                return self._err(
                    "every gene must have the same number of sample values."
                )
            matrix = np.asarray(rows, dtype=float)
            n_samples = matrix.shape[1]
            samples = [str(s) for s in (args.get("samples") or [])]
            if len(samples) != n_samples:
                samples = [f"sample_{j + 1}" for j in range(n_samples)]
        else:
            return self._err(
                "Provide expression ({gene: [value_per_sample]}) — a genes x samples matrix."
            )
        if len(genes) < 10:
            return self._err("At least 10 genes are required.")
        return genes, samples, matrix

    def _parse_gene_sets(self, args: Dict[str, Any]):
        gs = args.get("gene_sets")
        if isinstance(gs, dict) and gs:
            return {str(k): [str(x) for x in v] for k, v in gs.items()}, None
        single = args.get("gene_set")
        if isinstance(single, (list, tuple)) and single:
            return {"gene_set": [str(x) for x in single]}, None
        return None, self._err(
            "Provide gene_sets ({name: [genes]}) or gene_set ([genes])."
        )

    @staticmethod
    def _err(message: str) -> Dict[str, Any]:
        return {"status": "error", "error": message, "source": "SSGSEATool"}
