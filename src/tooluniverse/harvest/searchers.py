from __future__ import annotations
import os
import re
import logging
import requests
import json
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

logger = logging.getLogger("HarvestSearch")
DEFAULT_TIMEOUT = int(os.getenv("HARVEST_TIMEOUT_S", "8"))


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str


def _clean_host(url: str) -> str:
    return re.sub(r"^https?://", "", url or "").split("/")[0].lower()


def _normalize_candidate_url(url: str) -> str:
    return (url or "").strip()


# ---------------- CKAN adapter ----------------
def _search_ckan(query: str, rows: int, base_url: str) -> List[SearchResult]:
    out: List[SearchResult] = []
    try:
        r = requests.get(
            base_url, params={"q": query, "rows": rows}, timeout=DEFAULT_TIMEOUT
        )
        r.raise_for_status()
        payload = r.json()
        # CKAN payload guard
        result = (payload or {}).get("result") or {}
        for pkg in result.get("results", []):
            title = pkg.get("title") or pkg.get("name") or "CKAN dataset"
            notes = (pkg.get("notes") or "")[:240]
            for res in pkg.get("resources") or []:
                res_url = _normalize_candidate_url(res.get("url") or "")
                if not res_url:
                    continue
                out.append(
                    SearchResult(
                        title=title,
                        url=res_url,
                        snippet=notes,
                        source=f"ckan:{_clean_host(base_url)}",
                    )
                )
    except Exception as e:
        logger.debug("CKAN search failed for %s: %s", base_url, e)
    return out


CATALOG_ADAPTERS = {
    "ckan": _search_ckan,
}


def search_for_apis(
    query: str, rows: int = 100, catalogs: Optional[List[Dict[str, Any]]] = None
) -> List[SearchResult]:
    """Search across configured catalogs.
    catalogs: list of dicts, e.g. [{"type": "ckan", "url": "https://.../api/3/action/package_search"}]
    You can supply this via env HARVEST_CATALOGS='[ ... ]' or pass in directly.
    """
    results: List[SearchResult] = []
    catalogs = catalogs or []
    for cat in catalogs:
        ctype = (cat.get("type") or "").lower().strip()
        url = cat.get("url") or ""
        if not ctype or not url:
            continue
        adapter = CATALOG_ADAPTERS.get(ctype)
        if not adapter:
            logger.debug("Unknown catalog type %s, skipping", ctype)
            continue
        results.extend(adapter(query=query, rows=rows, base_url=url))
    return results
