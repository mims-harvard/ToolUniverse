from __future__ import annotations
from functools import lru_cache
from typing import Dict, List

# Conservative allow/deny fragments. We still compute a trust score as a gradient.
ALLOWED_FRAGMENTS: List[str] = [
    # government & intergovernmental
    ".gov",
    ".mil",
    ".gob",
    ".gouv",
    ".go.",
    ".govt.nz",
    ".gc.ca",
    "who.int",
    "worldbank.org",
    "oecd.org",
    "europa.eu",
    "esa.int",
    # major scientific/health orgs
    "nih.gov",
    "niddk.nih.gov",
    "ninds.nih.gov",
    "ncbi.nlm.nih.gov",
    "data.cdc.gov",
    "api.cdc.gov",
    "fda.gov",
    "api.fda.gov",
    "epa.gov",
    "noaa.gov",
    "usgs.gov",
    "census.gov",
    "data.gov",
    "healthdata.gov",
    "data.cms.gov",
    "data.hrsa.gov",
    "data.hhs.gov",
    "ghoapi.azureedge.net",
]

BLOCKED_FRAGMENTS: List[str] = [
    "mirror",
    "docshare",
    "scribd.com",
    "sharepdf",
    "academia.edu",
    "stackprinter",
    "cachedview",
    "wayback",
    "pirated",
    "scrapeops",
]


@lru_cache(maxsize=4096)
def domain_blocked(host: str) -> bool:
    h = (host or "").lower()
    return any(b in h for b in BLOCKED_FRAGMENTS)


@lru_cache(maxsize=4096)
def domain_allowed(host: str) -> bool:
    # allow if any strong allow fragment present AND not blocked
    h = (host or "").lower()
    if domain_blocked(h):
        return False
    return any(a in h for a in ALLOWED_FRAGMENTS)


@lru_cache(maxsize=4096)
def trust_score(host: str) -> Dict:
    """Return a graded trust score in [0,1] with reasons for ranking.
    We don't *block* here (that's domain_blocked); we provide a signal for ranker.
    """
    h = (host or "").lower()
    score = 0.0
    reasons: List[str] = []
    if domain_blocked(h):
        return {"score": 0.0, "reasons": ["blocked"]}

    # strong positives
    if any(
        tld in h
        for tld in (".gov", "who.int", "worldbank.org", "europa.eu", "oecd.org")
    ):
        score += 0.65
        reasons.append("gov/igo domain")
    if any(
        seg in h
        for seg in (
            "nih.gov",
            "ncbi.nlm.nih.gov",
            "fda.gov",
            "epa.gov",
            "noaa.gov",
            "usgs.gov",
            "census.gov",
        )
    ):
        score += 0.2
        reasons.append("major science/health org")
    # medium positives
    if h.startswith("api.") or "/api" in h:
        score += 0.05
        reasons.append("api host")
    # slight boost for data portals
    if any(
        seg in h
        for seg in (
            "data.gov",
            "healthdata.gov",
            "data.cms.gov",
            "data.cdc.gov",
            "data.europa.eu",
        )
    ):
        score += 0.08
        reasons.append("open data portal")

    score = max(0.0, min(1.0, score))
    return {"score": round(score, 3), "reasons": reasons}
