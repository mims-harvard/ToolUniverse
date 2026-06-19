"""Co-expression module detection from an expression matrix (NumPy + NetworkX).

Builds a gene co-expression network from a genes x samples expression matrix and
partitions it into modules of co-regulated genes — the analysis at the heart of
WGCNA-style workflows. Genes are connected by their pairwise correlation,
soft-thresholded (``|r|^power``, the WGCNA scale-free emphasis), and the network
is partitioned by greedy modularity maximization. For each module a **module
eigengene** (the first principal component of the module's expression) summarizes
its activity across samples.

This is a dependency-light implementation (NumPy correlation + NetworkX community
detection + a NumPy SVD eigengene), not a full WGCNA port — it omits the
topological-overlap matrix and dynamic tree cut, using modularity communities
instead. It is deterministic and testable directly.

``run()`` returns a ``{status, data, metadata}`` dict and never raises.

Reference
---------
Langfelder P, Horvath S. "WGCNA: an R package for weighted correlation network
analysis." BMC Bioinformatics 9, 559 (2008).
"""

from typing import Any, Dict, List, Optional

import networkx as nx
import numpy as np

from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("CoexpressionModuleTool")
class CoexpressionModuleTool(BaseTool):
    """Detect co-expression modules + module eigengenes from an expression matrix."""

    def __init__(self, tool_config: Optional[Dict[str, Any]] = None):
        super().__init__(tool_config)
        self.tool_config = tool_config or {}

    # ------------------------------------------------------------------ run
    def run(self, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        args = arguments or {}
        parsed = self._parse_expression(args)
        if isinstance(parsed, dict):
            return parsed
        genes, matrix = parsed  # matrix: genes x samples

        power = int(args.get("power") or 6)
        threshold = float(args.get("correlation_threshold") or 0.5)
        min_size = int(args.get("min_module_size") or 5)

        corr = np.corrcoef(matrix)
        corr = np.nan_to_num(corr)  # constant genes -> 0 correlation
        n = len(genes)

        g = nx.Graph()
        g.add_nodes_from(range(n))
        iu = np.triu_indices(n, k=1)
        for i, j in zip(*iu):
            r = abs(corr[i, j])
            if r >= threshold:
                g.add_edge(int(i), int(j), weight=r**power)

        communities = nx.community.greedy_modularity_communities(g, weight="weight")
        modules = []
        for k, comm in enumerate(communities):
            idx = sorted(comm)
            if len(idx) < min_size:
                continue
            modules.append(
                {
                    "module_id": f"M{len(modules) + 1}",
                    "size": len(idx),
                    "genes": [genes[i] for i in idx],
                    "eigengene": self._eigengene(matrix[idx]),
                }
            )

        assigned = sum(m["size"] for m in modules)
        return {
            "status": "success",
            "data": {
                "n_genes": n,
                "n_samples": int(matrix.shape[1]),
                "n_modules": len(modules),
                "n_unassigned": n - assigned,
                "modules": modules,
            },
            "metadata": {
                "method": "co-expression modules (soft-thresholded correlation + modularity)",
                "power": power,
                "correlation_threshold": threshold,
                "min_module_size": min_size,
                "note": (
                    "Modules group co-expressed genes; eigengene = first PC of the "
                    "module's expression across samples (its summary profile). "
                    "Simplified WGCNA (no TOM / dynamic tree cut)."
                ),
            },
        }

    # -------------------------------------------------------------- helpers
    @staticmethod
    def _eigengene(block: np.ndarray) -> List[float]:
        """First principal component of a (genes x samples) block -> per-sample vector."""
        centered = block - block.mean(axis=1, keepdims=True)
        # right singular vector of the centered block = sample-space PC1
        _, _, vt = np.linalg.svd(centered, full_matrices=False)
        eig = vt[0]
        # sign-align so the eigengene tracks the module's mean expression
        if np.corrcoef(eig, block.mean(axis=0))[0, 1] < 0:
            eig = -eig
        return [float(x) for x in eig]

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
            if len({len(r) for r in rows}) != 1:
                return self._err(
                    "every gene must have the same number of sample values."
                )
            matrix = np.asarray(rows, dtype=float)
        else:
            return self._err(
                "Provide expression ({gene: [value_per_sample]}) — a genes x samples matrix."
            )
        if len(genes) < 4:
            return self._err("At least 4 genes are required to build a network.")
        if matrix.shape[1] < 3:
            return self._err("At least 3 samples are required to compute correlations.")
        return genes, matrix

    @staticmethod
    def _err(message: str) -> Dict[str, Any]:
        return {"status": "error", "error": message, "source": "CoexpressionModuleTool"}
