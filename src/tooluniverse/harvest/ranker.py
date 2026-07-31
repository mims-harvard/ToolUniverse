from __future__ import annotations
import math
from typing import List, Dict

def _sim(a: str, b: str) -> float:
    a,b = (a or "").lower(), (b or "").lower()
    if not a or not b:
        return 0.0
    aset, bset = set(a.split()), set(b.split())
    overlap = len(aset & bset)
    return overlap / (len(aset) + 1e-6)

def rank_candidates(query: str, candidates: List[Dict]) -> List[Dict]:
    def score(c: Dict) -> float:
        trust = float(((c.get("trust") or {}).get("score") or 0.0))
        h = c.get("health") or {}
        live = 1.0 if (h.get("ok") and (h.get("status",0) < 500)) else 0.0
        lat = h.get("latency_ms") or 1500
        lat_norm = max(0.0, 1.0 - min(lat, 4000)/4000.0)
        fit = max(_sim(query, c.get("name","")), _sim(query, c.get("doc_url","")))
        has_spec = 1.0 if c.get("openapi_url") else 0.2 if c.get("endpoints") else 0.0
        cors = 0.3 if (c.get("cors") or {}).get("preflight") else 0.0
        match_bonus = float(c.get("_match_score") or 0.0)
        return (
            0.25 * trust
            + 0.2 * (live * lat_norm)
            + 0.23 * fit
            + 0.1 * has_spec
            + 0.05 * cors
            + (0.35 * math.log1p(match_bonus) if match_bonus > 0 else 0.0)
        )

    ranked = sorted(candidates, key=score, reverse=True)
    for i, c in enumerate(ranked):
        c["_rank_score"] = round(score(c), 4)
    return ranked
