#!/usr/bin/env python3
"""Network proximity Z-score between drug targets and a disease gene set.

Implements the Guney/Barabasi (2016) closest-distance network proximity — the
largest component of the Network Pharmacology Score — which ToolUniverse has no
tool for (it needs the full interactome + a degree-matched random null, i.e.
graph computation, not a REST call).

Method:
  d_c(T, S) = mean over drug targets t of min over disease genes s of
              shortest_path_length(t, s)   in the human PPI network
  Z = (d_c - mean(d_c_random)) / sd(d_c_random)
where the random reference is `n_rand` target-sized gene sets drawn
degree-matched to the real targets. Z < -0.15 (and a low empirical p) indicates
the drug targets are significantly closer to the disease module than chance.

Network: STRING v12 human, high-confidence edges (combined_score >= 700),
downloaded once and cached. Requires networkx + a one-time ~MB download.

Usage:
    python network_proximity.py --targets EGFR,ERBB2 --disease TP53,KRAS,PIK3CA
    python network_proximity.py --targets-file t.txt --disease-file d.txt --n-rand 1000
"""

from __future__ import annotations

import argparse
import gzip
import os
import random
import statistics
import sys
import tempfile
import urllib.request

STRING_LINKS = "https://stringdb-downloads.org/download/protein.links.v12.0/9606.protein.links.v12.0.txt.gz"
STRING_INFO = "https://stringdb-downloads.org/download/protein.info.v12.0/9606.protein.info.v12.0.txt.gz"
CACHE_DIR = os.path.join(tempfile.gettempdir(), "string_cache")
MIN_SCORE = 700  # high-confidence


def _cached(url, name):
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, name)
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        sys.stderr.write(f"Downloading {name} (one-time)...\n")
        urllib.request.urlretrieve(url, path)
    return path


def build_graph():
    """Build the high-confidence human PPI graph with gene-symbol nodes."""
    import networkx as nx

    # STRING protein ID -> gene symbol
    id2sym = {}
    with gzip.open(_cached(STRING_INFO, "string_info.txt.gz"), "rt") as fh:
        next(fh, None)
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 2:
                id2sym[parts[0]] = parts[1]

    g = nx.Graph()
    with gzip.open(_cached(STRING_LINKS, "string_links.txt.gz"), "rt") as fh:
        next(fh, None)
        for line in fh:
            a, b, score = line.split()
            if int(score) < MIN_SCORE:
                continue
            sa, sb = id2sym.get(a), id2sym.get(b)
            if sa and sb and sa != sb:
                g.add_edge(sa, sb)
    return g


def _closest_distance(g, sources, targets_set, sp_cache):
    import networkx as nx

    dists = []
    for s in sources:
        if s not in g:
            continue
        if s not in sp_cache:
            sp_cache[s] = nx.single_source_shortest_path_length(g, s)
        d = sp_cache[s]
        reachable = [d[t] for t in targets_set if t in d]
        if reachable:
            dists.append(min(reachable))
    return statistics.mean(dists) if dists else None


def _degree_bins(g):
    bins = {}
    for node, deg in g.degree():
        bins.setdefault(deg, []).append(node)
    return bins


def _degree_matched_sample(g, ref_nodes, bins, rng):
    out = []
    for n in ref_nodes:
        if n not in g:
            continue
        deg = g.degree(n)
        # widen the bin until it has candidates
        for w in range(0, 200):
            pool = []
            for d in range(max(1, deg - w), deg + w + 1):
                pool += bins.get(d, [])
            if len(pool) > 5:
                out.append(rng.choice(pool))
                break
    return out


def proximity(targets, disease, n_rand=1000, seed=42):
    g = build_graph()
    targets = [t for t in targets if t in g]
    disease = set(d for d in disease if d in g)
    if not targets or not disease:
        return {"error": "no targets or disease genes map to the STRING network",
                "mapped_targets": targets, "mapped_disease": len(disease)}

    sp_cache = {}
    d_c = _closest_distance(g, targets, disease, sp_cache)

    rng = random.Random(seed)
    bins = _degree_bins(g)
    rand_d = []
    for _ in range(n_rand):
        rand_targets = _degree_matched_sample(g, targets, bins, rng)
        val = _closest_distance(g, rand_targets, disease, sp_cache)
        if val is not None:
            rand_d.append(val)

    mean_r = statistics.mean(rand_d)
    sd_r = statistics.pstdev(rand_d) or 1e-9
    z = (d_c - mean_r) / sd_r
    p = sum(1 for v in rand_d if v <= d_c) / len(rand_d)
    return {
        "d_c": round(d_c, 4),
        "z_score": round(z, 3),
        "empirical_p": round(p, 4),
        "random_mean": round(mean_r, 4),
        "random_sd": round(sd_r, 4),
        "n_random": len(rand_d),
        "mapped_targets": len(targets),
        "mapped_disease": len(disease),
        # Guney et al. use Z < -0.15 as the proximity threshold; empirical_p is a
        # coarser support statistic (use n_rand >= 1000 for a stable p).
        "interpretation": (
            f"targets proximal to the disease module (Z={round(z, 2)} < -0.15)"
            if z < -0.15 else
            "no significant proximity (targets not closer than chance)"
        ),
    }


def _read_list(path):
    return [x.strip() for x in open(path) if x.strip()]


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--targets")
    p.add_argument("--disease")
    p.add_argument("--targets-file")
    p.add_argument("--disease-file")
    p.add_argument("--n-rand", type=int, default=1000)
    args = p.parse_args(argv)
    targets = _read_list(args.targets_file) if args.targets_file else (args.targets or "").split(",")
    disease = _read_list(args.disease_file) if args.disease_file else (args.disease or "").split(",")
    targets = [t for t in targets if t]
    disease = [d for d in disease if d]
    if not targets or not disease:
        p.error("provide --targets and --disease (comma-separated) or the -file forms")
    import json

    print(json.dumps(proximity(targets, disease, args.n_rand), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
