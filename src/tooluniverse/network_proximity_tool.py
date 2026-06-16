"""
Network proximity / separation between two node sets for ToolUniverse.

Local-compute, deterministic graph distance between two node sets, with the
standard family of measures from Guney/Barabasi (2016) and Menche (2015) and a
degree-matched random Z-score. The canonical use is network pharmacology ("are a
drug's targets close to a disease module?"), but the computation is
domain-agnostic — it works for any two node sets on any graph (two pathways, two
marker-gene sets, two GO terms, …).

Measures (all on shortest-path lengths in the supplied graph):
  closest     d_c(A,B) = mean over a of  min over b  d(a, b)               (Guney 2016)
  shortest    d_s(A,B) = mean over reachable (a,b) pairs of  d(a, b)
  separation  s_AB     = d_AB - (d_AA + d_BB)/2                            (Menche 2015)
              where d_XY is the symmetric closest distance between sets.
A low value (and low empirical p vs a degree-matched null) means the two sets sit
closer / more overlapping than chance. For `separation`, s_AB < 0 ⇒ overlapping
modules, s_AB > 0 ⇒ topologically separated.

Pure networkx + NumPy (both core deps); no network call, no API key. The caller
supplies the graph (inline `edges` or a 2-column `edgelist_path`), so no
particular interactome or species is baked in.
"""

import csv as _csv
import os
import random
from typing import Any, Dict, List, Optional

from .base_tool import BaseTool
from .tool_registry import register_tool

_DEFAULT_N_RAND = 1000
_DEFAULT_SEED = 42
_MEASURES = ("closest", "shortest", "separation")


def _err(msg: str) -> Dict[str, Any]:
    return {"status": "error", "error": msg}


def _ok(data: Dict[str, Any], **metadata) -> Dict[str, Any]:
    meta = {"engine": "networkx"}
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


def _lengths(graph, nx, node, cache) -> Dict[Any, int]:
    """Shortest-path lengths from `node` to all reachable nodes (memoized)."""
    if node not in cache:
        cache[node] = nx.single_source_shortest_path_length(graph, node)
    return cache[node]


def _closest_to_set(graph, nx, node, node_set, cache) -> Optional[int]:
    """Min shortest-path length from `node` to any member of `node_set`."""
    lengths = _lengths(graph, nx, node, cache)
    reachable = [lengths[t] for t in node_set if t in lengths]
    return min(reachable) if reachable else None


def _within_closest(graph, nx, nodes, cache) -> float:
    """Mean over nodes of the distance to the nearest OTHER node in the set."""
    s = set(nodes)
    vals = []
    for n in nodes:
        lengths = _lengths(graph, nx, n, cache)
        reachable = [lengths[o] for o in s if o != n and o in lengths]
        if reachable:
            vals.append(min(reachable))
    return sum(vals) / len(vals) if vals else 0.0


def _closest_distances(graph, nx, src_nodes, dst_set, cache) -> List[int]:
    """Per-source closest distance into `dst_set`, skipping unreachable sources."""
    return [
        d
        for n in src_nodes
        if (d := _closest_to_set(graph, nx, n, dst_set, cache)) is not None
    ]


def _measure(graph, nx, a, b, kind, cache) -> Optional[float]:
    """Compute the requested set-distance measure, or None if undefined/disjoint."""
    aset, bset = set(a), set(b)
    if kind == "closest":
        vals = _closest_distances(graph, nx, a, bset, cache)
        return sum(vals) / len(vals) if vals else None
    if kind == "shortest":
        pair = []
        for n in a:
            lengths = _lengths(graph, nx, n, cache)
            pair += [lengths[t] for t in bset if t in lengths]
        return sum(pair) / len(pair) if pair else None
    if kind == "separation":
        ab = _closest_distances(graph, nx, a, bset, cache)
        ba = _closest_distances(graph, nx, b, aset, cache)
        if not ab or not ba:
            return None
        d_ab = (sum(ab) + sum(ba)) / (len(ab) + len(ba))
        d_aa = _within_closest(graph, nx, a, cache)
        d_bb = _within_closest(graph, nx, b, cache)
        return d_ab - (d_aa + d_bb) / 2.0
    return None


def _degree_bins(graph) -> Dict[int, List[Any]]:
    bins: Dict[int, List[Any]] = {}
    for node, deg in graph.degree():
        bins.setdefault(deg, []).append(node)
    return bins


def _degree_matched(ref_nodes, bins, graph, rng) -> List[Any]:
    """Sample one degree-matched node per reference node (with replacement)."""
    return [rng.choice(bins[graph.degree(n)]) for n in ref_nodes]


@register_tool("NetworkProximityTool")
class NetworkProximityTool(BaseTool):
    """Network proximity / separation between two node sets (Guney/Menche)."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            import networkx as nx
            import numpy as np
        except Exception:  # pragma: no cover - core deps, defensive
            return _err("networkx/numpy not available (both are core dependencies).")

        measure = arguments.get("measure") or "closest"
        if measure not in _MEASURES:
            return _err(f"'measure' must be one of {_MEASURES}, got {measure!r}.")

        # Domain-neutral set_a/set_b, with drug-pharmacology aliases.
        a_in = arguments.get("set_a") or arguments.get("targets")
        b_in = arguments.get("set_b") or arguments.get("disease_genes")
        if not a_in or not b_in:
            return _err(
                "Provide two non-empty node sets: 'set_a'/'set_b' "
                "(or the aliases 'targets'/'disease_genes')."
            )
        set_a = [str(x) for x in a_in]
        set_b = [str(x) for x in b_in]

        edges = _load_edges(arguments)
        if isinstance(edges, dict):
            return edges
        graph = nx.Graph()
        graph.add_edges_from(edges)
        if graph.number_of_nodes() == 0:
            return _err("network has no nodes/edges.")

        a = [n for n in set_a if n in graph]
        b = [n for n in set_b if n in graph]
        missing_a = [n for n in set_a if n not in graph]
        missing_b = [n for n in set_b if n not in graph]
        if not a or not b:
            return _err(
                f"set_a or set_b has no nodes in the network "
                f"(set_a in net: {len(a)}, set_b in net: {len(b)})."
            )

        cache: Dict[Any, Dict[Any, int]] = {}
        observed = _measure(graph, nx, a, b, measure, cache)
        if observed is None:
            return _err("set_a and set_b are in disconnected components.")

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
            ra = _degree_matched(a, bins, graph, rng)
            rb = _degree_matched(b, bins, graph, rng)
            dr = _measure(graph, nx, ra, rb, measure, {})
            if dr is not None:
                randoms.append(dr)

        data: Dict[str, Any] = {
            "measure": measure,
            "value": round(float(observed), 6),
            "n_set_a_in_network": len(a),
            "n_set_b_in_network": len(b),
            "nodes_in_network": graph.number_of_nodes(),
            "missing_set_a": missing_a or None,
            "missing_set_b": missing_b or None,
        }
        if len(randoms) >= 2:
            arr = np.asarray(randoms, dtype=float)
            mu, sd = float(arr.mean()), float(arr.std(ddof=0))
            p = float((arr <= observed).sum()) / len(
                arr
            )  # one-sided: closer than chance
            data.update(
                {
                    "z_score": round((observed - mu) / sd, 6) if sd > 0 else None,
                    "p_value": round(p, 6),
                    "random_mean": round(mu, 6),
                    "random_std": round(sd, 6),
                    "n_randomizations": len(randoms),
                }
            )
        return _ok(data, method=f"{measure}_distance")
