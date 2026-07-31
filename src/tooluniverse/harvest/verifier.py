from __future__ import annotations
import os
import time
import logging
import requests
from typing import Dict, Optional

logger = logging.getLogger("HarvestVerify")
DEFAULT_TIMEOUT = int(os.getenv("HARVEST_TIMEOUT_S", "8"))
SIZE_LIMIT = int(os.getenv("HARVEST_MAX_BYTES", "2000000"))
JSON_ACCEPT = {"Accept": "application/json"}


def _head(url: str, timeout=None):
    try:
        return requests.head(
            url, timeout=timeout or DEFAULT_TIMEOUT, allow_redirects=True
        )
    except requests.RequestException:
        return None


def _health_probe(url: str, timeout=None) -> Dict:
    t0 = time.time()
    try:
        rh = _head(url, timeout)
        if rh is not None:
            clen = int(rh.headers.get("Content-Length") or 0)
            if clen and clen > SIZE_LIMIT:
                return {
                    "ok": False,
                    "status": rh.status_code,
                    "skipped": f"large({clen})",
                }
        r = requests.get(url, timeout=timeout or DEFAULT_TIMEOUT, headers=JSON_ACCEPT)
        return {
            "ok": r.status_code < 500,
            "status": r.status_code,
            "latency_ms": int((time.time() - t0) * 1000),
            "ctype": r.headers.get("Content-Type", ""),
        }
    except requests.RequestException as e:
        return {"ok": False, "status": 0, "error": str(e)}


def verify_candidate(result, timeout_s: Optional[int] = None) -> Optional[Dict]:
    url = (result.url or "").strip()
    if not url:
        return None
    health = _health_probe(url, timeout=timeout_s)
    return {"name": result.title, "url": url, "health": health, "source": result.source}
