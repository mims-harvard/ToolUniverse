"""Gene Set Variation Analysis (GSVA, pure NumPy).

GSVA (Hänzelmann, Castelo & Guinney, BMC Bioinformatics 2013) turns a gene
expression matrix (genes x samples) into a gene_set x sample pathway-activity
matrix *without phenotype labels*, like ssGSEA — but with two distinguishing
steps that make its scores comparable across heterogeneous samples and
characteristically bimodal:

  1. **Kernel-smoothed CDF per gene across samples** — each gene's expression is
     converted to a non-parametric, gene-specific quantile (Gaussian kernel for
     continuous/log data), so a gene is judged relative to its own distribution
     across the cohort, not on an absolute scale.
  2. **Symmetric rank random walk with a max-deviation difference score**
     (``mx_diff=True``, the GSVA default): the per-sample enrichment is
     ``ES_pos + ES_neg`` of a Kolmogorov-Smirnov-like walk over the centered
     ranks, giving signed scores centered near zero (positive = the set is
     up-regulated in that sample relative to the cohort).

This is the GSVA algorithm in deterministic rank-based math (no R, no
permutation), so it runs and is testable directly. It complements ``ssGSEA``
(absolute single-sample score) and ``GSEA_prerank`` (one ranked contrast).

``run()`` returns a ``{status, data, metadata}`` dict and never raises.

Reference
---------
Hänzelmann S, Castelo R, Guinney J. "GSVA: gene set variation analysis for
microarray and RNA-seq data." BMC Bioinformatics 14, 7 (2013).
"""

from typing import Any, Dict, Optional

import numpy as np

from .base_tool import BaseTool
from .tool_registry import register_tool


def _phi(z: np.ndarray) -> np.ndarray:
    """Standard-normal CDF via a vectorized erf (Abramowitz & Stegun 7.1.26).

    Max absolute error ~1.5e-7 — far below the precision rank-ordering needs and
    fully NumPy-vectorized (no scipy, which is not a core dependency).
    """
    x = z / np.sqrt(2.0)
    sign = np.sign(x)
    ax = np.abs(x)
    t = 1.0 / (1.0 + 0.3275911 * ax)
    poly = (
        ((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t
        + 0.254829592
    ) * t
    erf = sign * (1.0 - poly * np.exp(-ax * ax))
    return 0.5 * (1.0 + erf)


def _rankdata_avg(a: np.ndarray) -> np.ndarray:
    """Average ranks (1-based), ties resolved by their mean rank (scipy algorithm)."""
    sorter = np.argsort(a, kind="mergesort")
    inv = np.empty(len(a), dtype=int)
    inv[sorter] = np.arange(len(a))
    a_sorted = a[sorter]
    obs = np.r_[True, a_sorted[1:] != a_sorted[:-1]]
    dense = obs.cumsum()[inv]
    count = np.r_[np.nonzero(obs)[0], len(a)]
    return 0.5 * (count[dense] + count[dense - 1] + 1)


@register_tool("GSVATool")
class GSVATool(BaseTool):
    """Gene Set Variation Analysis: per-sample, label-free pathway activity."""

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

        tau_arg = args.get("tau")
        tau = float(tau_arg if tau_arg is not None else 1.0)
        mx_diff_arg = args.get("mx_diff")
        mx_diff = bool(mx_diff_arg if mx_diff_arg is not None else True)

        # 1. per-gene kernel CDF across samples, then 2. centered within-sample ranks
        rank_stat = self._rank_statistic(matrix)  # genes x samples, centered ranks

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
            mask = np.zeros(len(genes), dtype=bool)
            mask[idx] = True
            scores[name] = {
                samples[j]: self._gsva_score(rank_stat[:, j], mask, tau, mx_diff)
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
                "method": "GSVA (Hänzelmann et al. 2013)",
                "kcdf": "Gaussian",
                "tau": tau,
                "mx_diff": mx_diff,
                "note": (
                    "enrichment_scores[set][sample]; signed, centered near zero. "
                    "Positive = the set is up-regulated in that sample relative to "
                    "the cohort. Scores are comparable across samples and sets. "
                    "Supply log-scale (continuous) expression; gene sets from "
                    "MSigDB/Enrichr."
                ),
            },
        }

    # --------------------------------------------------------- rank statistic
    def _rank_statistic(self, matrix: np.ndarray) -> np.ndarray:
        """Kernel-CDF per gene, then centered within-sample ranks (genes x samples)."""
        density = self._gaussian_cdf_density(matrix)
        n_genes, n_samples = matrix.shape
        center = (n_genes + 1) / 2.0
        out = np.empty_like(density, dtype=float)
        for j in range(n_samples):
            out[:, j] = _rankdata_avg(density[:, j]) - center
        return out

    @staticmethod
    def _gaussian_cdf_density(matrix: np.ndarray) -> np.ndarray:
        """Per-gene Gaussian-kernel CDF across samples (bandwidth = sd/4, GSVA C code)."""
        n_genes, n_samples = matrix.shape
        sd = matrix.std(axis=1, ddof=1)  # per-gene SD (n-1, matching R sd())
        bw = sd / 4.0
        dens = np.empty_like(matrix, dtype=float)
        for i in range(n_genes):
            xi = matrix[i]
            if bw[i] > 0:
                # F_i(x_ij) = mean_k Phi((x_ij - x_ik) / bw_i)
                z = (xi[:, None] - xi[None, :]) / bw[i]
                dens[i] = _phi(z).mean(axis=1)
            else:
                # constant gene: fall back to the mid-rank empirical CDF
                greater = (xi[:, None] > xi[None, :]).astype(float)
                equal = (xi[:, None] == xi[None, :]).astype(float)
                dens[i] = (greater + 0.5 * equal).mean(axis=1)
        return dens

    # ----------------------------------------------------------- gsva score
    @staticmethod
    def _gsva_score(
        rank_stat: np.ndarray, mask: np.ndarray, tau: float, mx_diff: bool
    ) -> float:
        """KS-like random walk over centered ranks for one sample / one gene set."""
        n = len(rank_stat)
        n_set = int(mask.sum())
        if n_set == 0 or n_set == n:
            return 0.0
        order = np.argsort(rank_stat, kind="mergesort")[::-1]  # high rank first
        rs = rank_stat[order]
        hits = mask[order]
        weights = np.abs(rs) ** tau
        hit_sum = float((weights * hits).sum())
        if hit_sum == 0:
            return 0.0
        step_hit = np.where(hits, weights / hit_sum, 0.0)
        step_miss = np.where(hits, 0.0, 1.0 / (n - n_set))
        running = np.cumsum(step_hit - step_miss)
        es_pos = float(running.max())
        es_neg = float(running.min())
        if mx_diff:
            return es_pos + es_neg
        # classic KS: the single largest-magnitude deviation
        return es_pos if es_pos > -es_neg else es_neg

    # -------------------------------------------------------------- inputs
    def _parse_expression(self, args: Dict[str, Any]):
        expr = args.get("expression")
        if not (isinstance(expr, dict) and expr):
            return self._err(
                "Provide expression ({gene: [value_per_sample]}) — a genes x samples matrix."
            )
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
            return self._err("every gene must have the same number of sample values.")
        matrix = np.asarray(rows, dtype=float)
        n_samples = matrix.shape[1]
        if n_samples < 2:
            return self._err(
                "At least 2 samples are required (GSVA normalizes each gene across samples)."
            )
        if len(genes) < 10:
            return self._err("At least 10 genes are required.")
        samples = [str(s) for s in (args.get("samples") or [])]
        if len(samples) != n_samples:
            samples = [f"sample_{j + 1}" for j in range(n_samples)]
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
        return {"status": "error", "error": message, "source": "GSVATool"}
