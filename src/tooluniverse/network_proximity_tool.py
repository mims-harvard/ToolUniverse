"""
Network proximity between two node sets for ToolUniverse.

Local-compute, deterministic implementation of the Guney/Barabasi (2016)
closest-distance network proximity and its degree-matched random Z-score — the
core of network-pharmacology "is this drug's targets close to the disease
module?" analyses. Pure networkx + NumPy (both core deps); no network call, no
API key.

It is general by construction: the caller supplies the network (inline edges or
a 2-column edgelist file) and the two node sets, so it works for any
interactome / metabolic / custom graph — it does not bake in a particular
database or species.

  d_c(S, T) = mean over s in S of  min over t in T of  shortest_path(s, t)
  Z = (d_c - mean(d_c_random)) / sd(d_c_random)
where the random reference draws degree-matched node sets of the same sizes.
A negative Z (and low empirical p) means S sits closer to T than chance.
"""

import csv as _csv
import os
import random
from typing import Any, Dict, List, Optional

from .base_tool import BaseTool
from .tool_registry import register_tool

_DEFAULT_N_RAND = 1000
_DEFAULT_SEED = 42


def _err(msg: str) -> Dict[str, Any]:
    return {"status": "error", "error": msg}


def _ok(data: Dict[str, Any], **metadata) -> Dict[str, Any]:
    meta = {"engine": "networkx", "method": "Guney2016_closest_distance"}
    meta.update(metadata)
    return {"status": "success", "data": data, "metadata": meta}


def _load_edges(args: Dict[str, Any]) -> Any:
    """Return a list of (u, v) edges from inline `edges` or `edgelist_path`."""
    if args.get("edgelist_path"):
        path = os.path.expanduser(str(args["edgelist_path"]).strip())
        if not os.path.isfile(path):
            return _err(f"edgelist_path not found: {path}")
        delim = "\t" if path.endswith((".tsv", ".txt")) else ","
        edges = []
        try:
            with open(path, newline="") as fh:
                for row in _csv.reader(fh, delimiter=delim):
                    if len(row) >= 2 and row[0].strip() and row[1].strip():
                        edges.append((row[0].strip(), row[1].strip()))
        except Exception as e:  # pragma: no cover - defensive
            return _err(f"failed to read edgelist_path: {e}")
        return edges
    edges = args.get("edges")
    if not edges:
        return _err("Provide a network: 'edges' (inline pairs) or 'edgelist_path'.")
    out = []
    for e in edges:
        if not isinstance(e, (list, tuple)) or len(e) < 2:
            return _err(f"each edge must be a [source, target] pair, got {e!r}")
        out.append((str(e[0]), str(e[1])))
    return out


def _degree_bins(graph) -> Dict[Any, List[Any]]:
    """Map each node to the list of nodes sharing its degree (for degree match)."""
    bins: Dict[int, List[Any]] = {}
    for node, deg in graph.degree():
        bins.setdefault(deg, []).append(node)
    return bins


def _degree_matched(ref_nodes, bins, graph, rng) -> List[Any]:
    """Sample one degree-matched node per reference node (with replacement)."""
    return [rng.choice(bins[graph.degree(n)]) for n in ref_nodes]


def _closest_distance(graph, source_set, target_set, nx, cache) -> Optional[float]:
    """Mean over sources of the min shortest-path to any target. None if disjoint."""
    dists = []
    target_set = set(target_set)
    for s in source_set:
        if s not in cache:
            cache[s] = nx.single_source_shortest_path_length(graph, s)
        lengths = cache[s]
        reachable = [lengths[t] for t in target_set if t in lengths]
        if reachable:
            dists.append(min(reachable))
    if not dists:
        return None
    return sum(dists) / len(dists)


@register_tool("NetworkProximityTool")
class NetworkProximityTool(BaseTool):
    """Closest-distance network proximity + degree-matched Z-score (Guney 2016)."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            import networkx as nx
            import numpy as np
        except Exception:  # pragma: no cover - core deps, defensive
            return _err("networkx/numpy not available (both are core dependencies).")

        edges = _load_edges(arguments)
        if isinstance(edges, dict):
            return edges
        targets = arguments.get("targets")
        disease = arguments.get("disease_genes")
        if not targets or not disease:
            return _err("Provide non-empty 'targets' and 'disease_genes' node lists.")
        targets = [str(x) for x in targets]
        disease = [str(x) for x in disease]

        graph = nx.Graph()
        graph.add_edges_from(edges)
        if graph.number_of_nodes() == 0:
            return _err("network has no nodes/edges.")

        src = [n for n in targets if n in graph]
        tgt = [n for n in disease if n in graph]
        missing_targets = [n for n in targets if n not in graph]
        missing_disease = [n for n in disease if n not in graph]
        if not src or not tgt:
            return _err(
                "no 'targets' or no 'disease_genes' are present in the network "
                f"(targets in net: {len(src)}, disease in net: {len(tgt)})."
            )

        cache: Dict[Any, Dict[Any, int]] = {}
        d_c = _closest_distance(graph, src, tgt, nx, cache)
        if d_c is None:
            return _err("targets and disease_genes are in disconnected components.")

        try:
            n_rand = int(arguments.get("n_rand") or _DEFAULT_N_RAND)
        except (TypeError, ValueError):
            return _err("'n_rand' must be an integer.")
        seed = arguments.get("seed")
        seed = _DEFAULT_SEED if seed is None else int(seed)
        rng = random.Random(seed)
        bins = _degree_bins(graph)

        randoms = []
        for _ in range(n_rand):
            rs = _degree_matched(src, bins, graph, rng)
            rt = _degree_matched(tgt, bins, graph, rng)
            dr = _closest_distance(graph, rs, rt, nx, {})
            if dr is not None:
                randoms.append(dr)

        data: Dict[str, Any] = {
            "closest_distance": round(float(d_c), 6),
            "n_targets_in_network": len(src),
            "n_disease_in_network": len(tgt),
            "nodes_in_network": graph.number_of_nodes(),
            "missing_targets": missing_targets or None,
            "missing_disease_genes": missing_disease or None,
        }
        if len(randoms) >= 2:
            arr = np.asarray(randoms, dtype=float)
            mu, sd = float(arr.mean()), float(arr.std(ddof=0))
            z = round((d_c - mu) / sd, 6) if sd > 0 else None
            p = float((arr <= d_c).sum()) / len(arr)  # one-sided: closer than chance
            data.update(
                {
                    "z_score": z,
                    "p_value": round(p, 6),
                    "random_mean": round(mu, 6),
                    "random_std": round(sd, 6),
                    "n_randomizations": len(randoms),
                }
            )
        return _ok(data)
