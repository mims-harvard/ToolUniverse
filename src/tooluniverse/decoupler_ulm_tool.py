"""Transcription-factor / pathway activity inference by univariate linear model.

Given a per-gene statistic (e.g. a differential-expression t-statistic or
log-fold-change) and a regulatory network (source = TF or pathway, target =
gene, weight = mode of regulation), this tool infers an **activity score** per
source — the ``ulm`` (univariate linear model) method of decoupleR (Badia-i-
Mompel et al., Bioinformatics Advances 2022). It pairs naturally with the
DoRothEA / PROGENy networks already exposed via the OmniPath tools.

For each source it regresses the gene statistic on that source's edge weights
(weight for its targets, 0 otherwise) across all genes, and reports the
**t-value of the slope** as the activity: positive = the source's positive
targets are coordinately up (active), negative = repressed. This is exactly the
deterministic linear algebra decoupleR runs, reimplemented in NumPy, so it needs
no extra dependency and is testable directly.

``run()`` returns a ``{status, data, metadata}`` dict and never raises.

Reference
---------
Badia-i-Mompel P, Vélez Santiago J, Braunger J, et al. "decoupleR: ensemble of
computational methods to infer biological activities from omics data."
Bioinformatics Advances 2, vbac016 (2022).
"""

import math
from typing import Any, Dict, List, Optional

import numpy as np

from .base_tool import BaseTool
from .tool_registry import register_tool


def _norm_p(t: np.ndarray) -> np.ndarray:
    """Two-sided p-values for an array of t-scores (normal approx, no SciPy)."""
    return np.array(
        [2.0 * (1.0 - 0.5 * (1.0 + math.erf(abs(x) / math.sqrt(2.0)))) for x in t]
    )


@register_tool("DecouplerULMTool")
class DecouplerULMTool(BaseTool):
    """Infer TF/pathway activities from a gene statistic + a regulatory network."""

    def __init__(self, tool_config: Optional[Dict[str, Any]] = None):
        super().__init__(tool_config)
        self.tool_config = tool_config or {}

    # ------------------------------------------------------------------ run
    def run(self, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        args = arguments or {}
        stats = self._parse_stats(args)
        if isinstance(stats, dict) and "error" in stats:
            return stats
        genes, y = stats

        net = args.get("network")
        if not isinstance(net, (list, tuple)) or not net:
            return self._err(
                "network must be a non-empty list of {source, target, weight?} edges."
            )
        min_targets = int(args.get("min_targets") or 5)

        index = {g: i for i, g in enumerate(genes)}
        sources: Dict[str, Dict[int, float]] = {}
        for edge in net:
            if not isinstance(edge, dict):
                continue
            s, tgt = edge.get("source"), edge.get("target")
            if s is None or tgt is None or str(tgt) not in index:
                continue
            w = edge.get("weight", edge.get("mor", 1.0))
            try:
                w = float(w)
            except (TypeError, ValueError):
                w = 1.0
            sources.setdefault(str(s), {})[index[str(tgt)]] = w

        usable = {s: tw for s, tw in sources.items() if len(tw) >= min_targets}
        if not usable:
            return self._err(
                f"No source has >= {min_targets} targets present among the ranked "
                "genes. Check that network targets use the same gene IDs."
            )

        activities = self._ulm(y, usable, len(genes))
        activities.sort(key=lambda r: abs(r["activity"]), reverse=True)
        return {
            "status": "success",
            "data": {
                "n_genes": int(len(genes)),
                "n_sources_tested": len(activities),
                "activities": activities,
            },
            "metadata": {
                "method": "decoupleR ULM (univariate linear model)",
                "min_targets": min_targets,
                "note": (
                    "activity = t-value of the slope regressing the gene statistic "
                    "on the source's target weights. Positive = source active "
                    "(its positive targets are up); p uses a normal approximation."
                ),
            },
        }

    # ------------------------------------------------------------- ulm math
    @staticmethod
    def _ulm(y: np.ndarray, sources: Dict[str, Dict[int, float]], n_genes: int):
        """Univariate linear regression of y on each source's weight vector."""
        n = n_genes
        ybar = float(y.mean())
        syy = float(np.sum((y - ybar) ** 2))
        out = []
        for s, tw in sources.items():
            x = np.zeros(n)
            for gi, w in tw.items():
                x[gi] = w
            xbar = x.mean()
            sxx = float(np.sum((x - xbar) ** 2))
            if sxx <= 0:
                continue
            sxy = float(np.sum((x - xbar) * (y - ybar)))
            b1 = sxy / sxx
            rss = max(syy - b1 * sxy, 0.0)
            se = math.sqrt((rss / (n - 2)) / sxx) if n > 2 and sxx > 0 else 0.0
            t = b1 / se if se > 0 else 0.0
            out.append(
                {
                    "source": s,
                    "n_targets": int(len(tw)),
                    "activity": float(t),
                    "p_value": float(_norm_p(np.array([t]))[0]),
                }
            )
        return out

    # -------------------------------------------------------------- inputs
    def _parse_stats(self, args: Dict[str, Any]):
        gs = args.get("gene_stats")
        if isinstance(gs, dict) and gs:
            genes = [str(k) for k in gs]
            try:
                y = np.asarray([float(v) for v in gs.values()], dtype=float)
            except (TypeError, ValueError):
                return self._err("gene_stats values must be numbers.")
        elif args.get("genes") and args.get("stats"):
            genes = [str(g) for g in args["genes"]]
            try:
                y = np.asarray([float(v) for v in args["stats"]], dtype=float)
            except (TypeError, ValueError):
                return self._err("stats must be numbers.")
            if len(genes) != len(y):
                return self._err("genes and stats must have the same length.")
        else:
            return self._err(
                "Provide gene_stats ({gene: statistic}) or genes + stats lists."
            )
        if len(genes) < 10:
            return self._err("At least 10 genes are required.")
        return genes, y

    @staticmethod
    def _err(message: str) -> Dict[str, Any]:
        return {"status": "error", "error": message, "source": "DecouplerULMTool"}
