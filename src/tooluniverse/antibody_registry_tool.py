"""
Antibody Registry tool for ToolUniverse.

The Antibody Registry (antibodyregistry.org, a SciCrunch/RRID resource)
assigns a persistent RRID (e.g. ``AB_2298772``) to every research antibody
and records its vendor, catalog number, target, clonality, host/source
organism, conjugate, applications, and defining citation. Journals
increasingly require antibody RRIDs for reproducibility, so this tool lets an
agent (a) search 3M+ antibodies by target/keyword and (b) resolve a specific
RRID to its full provenance record.

API: https://www.antibodyregistry.org/api (public, no authentication).
Search uses the full-text endpoint ``/api/fts-antibodies?q=...``; ``/api/antibodies``
without a query simply lists the whole database.
"""

from typing import Any, Dict, List

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

ANTIBODY_API = "https://www.antibodyregistry.org/api"

# The raw record has ~38 fields, many internal (insert/curate timestamps, ix,
# feedback). Surface the scientifically useful subset plus the derived RRID.
_USEFUL_FIELDS = (
    "abName",
    "abTarget",
    "abTargetUniprotId",
    "abTargetEntrezId",
    "uniprotId",
    "clonality",
    "cloneId",
    "epitope",
    "targetSpecies",
    "sourceOrganism",
    "productConjugate",
    "productIsotype",
    "productForm",
    "applications",
    "vendorName",
    "vendorUrl",
    "catalogNum",
    "catAlt",
    "commercialType",
    "definingCitation",
    "numOfCitation",
    "comments",
    "url",
    "status",
)


def _normalize(item: Dict[str, Any]) -> Dict[str, Any]:
    """Trim a raw antibody record to useful fields and add the derived RRID."""
    out = {k: item.get(k) for k in _USEFUL_FIELDS if item.get(k) not in (None, "")}
    ab_id = item.get("abId")
    if ab_id is not None:
        out["rrid"] = f"AB_{ab_id}"
        out["ab_id"] = ab_id
    return out


@register_tool("AntibodyRegistryTool")
class AntibodyRegistryTool(BaseTool):
    """Search and resolve research antibodies in the Antibody Registry (RRID)."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout: int = tool_config.get("timeout", 30)
        self.operation: str = tool_config.get("fields", {}).get("operation", "search")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        operation = arguments.get("operation") or self.operation
        if operation == "search":
            return self._search(arguments)
        if operation == "get_by_rrid":
            return self._get_by_rrid(arguments)
        return {
            "status": "error",
            "error": f"Unknown operation: {operation}. Supported: search, get_by_rrid.",
        }

    def _request(self, path: str, params: Dict[str, Any] | None = None):
        try:
            resp = requests.get(
                f"{ANTIBODY_API}/{path}",
                params=params or {},
                headers={"Accept": "application/json"},
                timeout=self.timeout,
            )
        except requests.Timeout:
            return None, {
                "status": "error",
                "error": f"Antibody Registry request timed out after {self.timeout}s.",
            }
        except requests.exceptions.RequestException as e:
            return None, {
                "status": "error",
                "error": f"Failed to reach Antibody Registry: {str(e)}",
            }
        if resp.status_code != 200:
            return None, {
                "status": "error",
                "error": f"Antibody Registry returned HTTP {resp.status_code}",
                "detail": resp.text[:300],
            }
        try:
            return resp.json(), None
        except ValueError:
            return None, {
                "status": "error",
                "error": "Antibody Registry returned a non-JSON response.",
            }

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = arguments.get("query") or arguments.get("q")
        if not query or not str(query).strip():
            return {
                "status": "error",
                "error": "Parameter 'query' is required (e.g. a target like 'GFAP' or 'anti-CD3').",
            }
        try:
            size = max(1, min(int(arguments.get("size", 10)), 100))
            page = max(1, int(arguments.get("page", 1)))  # pages start at 1
        except (TypeError, ValueError):
            return {
                "status": "error",
                "error": "Parameters 'size' and 'page' must be integers.",
            }

        body, err = self._request(
            "fts-antibodies", {"q": str(query), "size": size, "page": page}
        )
        if err:
            return err

        items: List[Dict[str, Any]] = (
            body.get("items", []) if isinstance(body, dict) else []
        )
        return {
            "status": "success",
            "data": [_normalize(it) for it in items],
            "metadata": {
                "source": "Antibody Registry (antibodyregistry.org)",
                "query": str(query),
                "total_matches": body.get("totalElements")
                if isinstance(body, dict)
                else None,
                "returned": len(items),
                "page": page,
            },
        }

    def _get_by_rrid(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        rrid = arguments.get("rrid") or arguments.get("ab_id")
        if rrid is None or not str(rrid).strip():
            return {
                "status": "error",
                "error": "Parameter 'rrid' is required (e.g. 'AB_2298772' or '2298772').",
            }
        # Accept 'AB_2298772', 'RRID:AB_2298772', or a bare numeric id.
        numeric = str(rrid).strip().upper().replace("RRID:", "").replace("AB_", "")
        if not numeric.isdigit():
            return {
                "status": "error",
                "error": f"Invalid RRID '{rrid}'. Expected 'AB_<number>' or a numeric antibody id.",
            }

        body, err = self._request(f"antibodies/{numeric}")
        if err:
            return err

        records = body if isinstance(body, list) else [body]
        records = [r for r in records if isinstance(r, dict)]
        if not records:
            return {
                "status": "error",
                "error": f"No antibody found for RRID AB_{numeric}.",
            }
        return {
            "status": "success",
            "data": _normalize(records[0]),
            "metadata": {
                "source": "Antibody Registry (antibodyregistry.org)",
                "rrid": f"AB_{numeric}",
            },
        }
