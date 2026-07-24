"""Pre-ranked Gene Set Enrichment Analysis (GSEA, pure NumPy).

Given a ranked gene list (each gene scored by, e.g., a differential-expression
statistic) and one or more gene sets, this tool computes the Kolmogorov-Smirnov
style enrichment of each set at the top or bottom of the ranking — the
"pre-ranked GSEA" of Subramanian et al. (PNAS 2005), the analysis every RNA-seq
study runs after differential expression. It complements the existing
over-representation tools (Enrichr) by using the full ranked list rather than a
hard significance cutoff.

For each gene set it returns:
  * **ES**  — enrichment score (max running-sum deviation; sign = up/down)
  * **NES** — normalized ES (ES / mean |ES| of the matching-sign null)
  * **p_value** — permutation p (gene-label permutation of the ranking)
  * **leading_edge** — the genes driving the signal (those before the ES peak)

This is the deterministic GSEAPreranked algorithm with a seeded permutation null,
so it runs and is testable directly (no R, no MSigDB bundled — the caller
supplies the gene sets, e.g. from Enrichr/MSigDB).

``run()`` returns a ``{status, data, metadata}`` dict and never raises.

Reference
---------
Subramanian A, Tamayo P, Mootha VK, et al. "Gene set enrichment analysis: a
knowledge-based approach for interpreting genome-wide expression profiles."
PNAS 102, 15545-15550 (2005).
"""

from typing import Any, Dict, List, Optional

import numpy as np

from .base_tool import BaseTool
from .tool_registry import register_tool

_N_PERM = 1000
_SEED = 0


@register_tool("GSEAPrerankTool")
class GSEAPrerankTool(BaseTool):
    """Pre-ranked GSEA enrichment of gene sets against a ranked gene list."""

    def __init__(self, tool_config: Optional[Dict[str, Any]] = None):
        super().__init__(tool_config)
        self.tool_config = tool_config or {}

    # ------------------------------------------------------------------ run
    def run(self, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        args = arguments or {}
        ranking = self._parse_ranking(args)
        if isinstance(ranking, dict):
            return ranking
        genes, scores = ranking  # genes sorted by score, descending

        gene_sets, gs_error = self._parse_gene_sets(args)
        if gs_error is not None:
            return gs_error

        weight = float(args.get("weight") or 1.0)
        n_perm = int(args.get("n_permutations") or _N_PERM)
        index = {g: i for i, g in enumerate(genes)}
        rng = np.random.default_rng(_SEED)

        results = []
        for name, members in gene_sets.items():
            # dedup members (a set may list a gene twice) so a gene's weight is
            # not double-counted and the miss-step denominator stays correct.
            hits = np.array(
                sorted({index[g] for g in members if g in index}), dtype=int
            )
            if len(hits) < 2:
                results.append(
                    {"gene_set": name, "n_overlap": int(len(hits)), "skipped": True}
                )
                continue
            results.append(self._enrich(name, genes, scores, hits, weight, n_perm, rng))

        results.sort(key=lambda r: (r.get("p_value", 1.0), -abs(r.get("nes", 0.0))))
        return {
            "status": "success",
            "data": {
                "n_genes_ranked": int(len(genes)),
                "n_gene_sets": len(gene_sets),
                "results": results,
            },
            "metadata": {
                "method": "pre-ranked GSEA (Subramanian 2005)",
                "weight": weight,
                "n_permutations": n_perm,
                "note": (
                    "ES sign: positive = set enriched at the top of the ranking "
                    "(e.g. up-regulated), negative = bottom. NES normalizes for set "
                    "size; p is a seeded gene-label permutation. Supply gene sets "
                    "via the caller (e.g. an MSigDB/Enrichr library)."
                ),
            },
        }

    # ----------------------------------------------------------- enrichment
    def _enrich(self, name, genes, scores, hits, weight, n_perm, rng):
        es, leading = self._running_es(scores, hits, weight, return_leading=True)
        # Seeded permutation null: for each permutation, score a random set of
        # the same size by drawing distinct gene ranks. Draw order is fixed by
        # the seeded rng, so the null (and p-value) is reproducible.
        n_hits = len(hits)
        null = np.array(
            [
                self._running_es(
                    scores, rng.choice(len(genes), n_hits, replace=False), weight
                )
                for _ in range(n_perm)
            ]
        )
        # NES normalizes ES by the mean |ES| of the same-sign null. If no
        # permutation shares the sign of es, fall back to the full null's mean
        # |ES| (and to 1.0 if even that is zero, to avoid division by zero).
        same_sign = null[null * es >= 0]
        if same_sign.size:
            denom = float(np.mean(np.abs(same_sign)))
        else:
            denom = float(np.mean(np.abs(null))) or 1.0
        nes = es / denom if denom else 0.0
        # permutation p: fraction of null at least as extreme (same tail)
        if es >= 0:
            p = (np.sum(null >= es) + 1) / (n_perm + 1)
        else:
            p = (np.sum(null <= es) + 1) / (n_perm + 1)
        return {
            "gene_set": name,
            "n_overlap": int(len(hits)),
            "es": float(es),
            "nes": float(nes),
            "p_value": float(p),
            "direction": "up (top of ranking)"
            if es >= 0
            else "down (bottom of ranking)",
            "leading_edge": [genes[i] for i in leading],
        }

    @staticmethod
    def _running_es(scores, hits, weight, return_leading=False):
        """Weighted KS running-sum enrichment score over the ranked list."""
        n = len(scores)
        tag = np.zeros(n, dtype=bool)
        tag[hits] = True
        hit_w = np.abs(scores[hits]) ** weight
        n_r = hit_w.sum()
        if n_r == 0:
            return (0.0, []) if return_leading else 0.0
        inc = np.zeros(n)
        inc[hits] = hit_w / n_r
        dec = (~tag).astype(float) / (n - len(hits))
        running = np.cumsum(inc - dec)
        peak = int(np.argmax(np.abs(running)))
        es = float(running[peak])
        if not return_leading:
            return es
        # leading edge: set members up to (and including) the ES peak
        if es >= 0:
            leading = [i for i in hits if i <= peak]
        else:
            leading = [i for i in hits if i >= peak]
        return es, leading

    # -------------------------------------------------------------- inputs
    def _parse_ranking(self, args: Dict[str, Any]):
        ranked = args.get("ranked_genes")
        genes, scores = None, None
        if isinstance(ranked, dict) and ranked:
            genes = list(ranked.keys())
            try:
                scores = [float(v) for v in ranked.values()]
            except (TypeError, ValueError):
                return self._err("ranked_genes values must be numbers.")
        elif args.get("genes") and args.get("scores"):
            genes = list(args["genes"])
            try:
                scores = [float(v) for v in args["scores"]]
            except (TypeError, ValueError):
                return self._err("scores must be numbers.")
            if len(genes) != len(scores):
                return self._err("genes and scores must have the same length.")
        else:
            return self._err(
                "Provide ranked_genes (a {gene: score} object) or genes + scores lists."
            )
        if len(genes) < 10:
            return self._err("At least 10 ranked genes are required.")
        genes = [str(g) for g in genes]
        order = np.argsort(scores)[::-1]  # descending: highest score first
        genes = [genes[i] for i in order]
        scores = np.asarray(scores, dtype=float)[order]
        return genes, scores

    def _parse_gene_sets(self, args: Dict[str, Any]):
        """Return (gene_sets_dict, None) on success or (None, error_dict)."""
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
        return {"status": "error", "error": message, "source": "GSEAPrerankTool"}
