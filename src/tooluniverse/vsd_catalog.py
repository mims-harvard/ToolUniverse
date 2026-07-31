# src/tooluniverse/vsd_catalog.py
import os
import json
from pathlib import Path
from typing import List, Dict, Any

VSD_DIR = Path(
    os.environ.get("TOOLUNIVERSE_VSD_DIR", Path.home() / ".tooluniverse" / "vsd")
)
ALLOWLIST_PATH = VSD_DIR / "allowlist.json"
CATALOG_PATH = VSD_DIR / "catalog" / "vsd_catalog_candidates.json"


def load_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_allowlist(seed: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    user = load_json(ALLOWLIST_PATH) or []
    merged = {e["domain"]: e for e in seed}
    for e in user:
        merged[e["domain"]] = {**merged.get(e["domain"], {}), **e}
    return list(merged.values())


def load_catalog_candidates() -> List[Dict[str, Any]]:
    data = load_json(CATALOG_PATH) or []
    # normalize minimal fields and keep only candidates
    out = []
    for d in data:
        if d.get("status") not in (None, "candidate", "approved"):
            continue
        out.append(
            {
                "domain": d.get("domain"),
                "label": d.get("label") or d.get("domain"),
                "registry": d.get("registry") or "data.gov",
                "endpoint": d.get("endpoint"),
                "license": d.get("license") or "unknown",
                "trust": float(d.get("trust") or 0.7),
                "freshness": d.get("freshness") or "",
                "api_kind": d.get("api_kind") or "rest",
                "status": d.get("status") or "candidate",
                "tags": d.get("tags") or [],
            }
        )
    return out
