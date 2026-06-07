"""
iDigBio tools for ToolUniverse — biodiversity specimen records.

iDigBio aggregates 130M+ digitized biodiversity specimen records (museum, herbarium,
paleo collections) in Darwin Core format. These tools search records by taxon/locality
and retrieve a single record by UUID.

API: https://search.idigbio.org/v2  (public, no authentication, JSON)
"""

import json
from typing import Any, Dict

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

IDIGBIO_BASE = "https://search.idigbio.org/v2"
# Darwin-Core query fields users may filter on (passed through to iDigBio's rq).
_QUERY_FIELDS = (
    "scientificname",
    "genus",
    "family",
    "country",
    "stateprovince",
    "recordedby",
    "catalognumber",
    "collectioncode",
    "phylum",
    "class",
    "order",
)


def _summarize(item: Dict[str, Any]) -> Dict[str, Any]:
    idx = item.get("indexTerms", {}) or {}
    data = item.get("data", {}) or {}
    return {
        "uuid": item.get("uuid"),
        "scientific_name": idx.get("scientificname") or data.get("dwc:scientificName"),
        "family": idx.get("family"),
        "genus": idx.get("genus"),
        "taxon_rank": idx.get("taxonrank"),
        "country": idx.get("country") or data.get("dwc:country"),
        "state_province": idx.get("stateprovince"),
        "county": idx.get("county"),
        "recorded_by": data.get("dwc:recordedBy"),
        "catalog_number": idx.get("catalognumber"),
        "collection_code": data.get("dwc:collectionCode"),
        "occurrence_id": data.get("dwc:occurrenceID"),
    }


@register_tool("iDigBioSearchTool")
class iDigBioSearchTool(BaseTool):
    """Search iDigBio biodiversity specimen records by taxon/locality."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("fields", {}).get("timeout", 30)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        rq = {
            f: arguments[f].strip()
            for f in _QUERY_FIELDS
            if isinstance(arguments.get(f), str) and arguments[f].strip()
        }
        if not rq:
            return {
                "status": "error",
                "error": "Provide at least one query field: "
                + ", ".join(_QUERY_FIELDS),
            }
        try:
            limit = max(1, min(int(arguments.get("limit") or 10), 100))
        except (TypeError, ValueError):
            limit = 10

        params = {"rq": json.dumps(rq), "limit": limit}
        try:
            resp = requests.get(
                f"{IDIGBIO_BASE}/search/records/",
                params=params,
                headers={"Accept": "application/json"},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            payload = resp.json()
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"iDigBio request timed out after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"iDigBio request failed: {e}"}
        except ValueError:
            return {"status": "error", "error": "iDigBio returned a non-JSON response"}

        items = payload.get("items", []) or []
        return {
            "status": "success",
            "data": [_summarize(it) for it in items if isinstance(it, dict)],
            "metadata": {
                "total_available": payload.get("itemCount"),
                "returned": len(items),
                "query": rq,
                "source": "iDigBio",
            },
        }


@register_tool("iDigBioRecordTool")
class iDigBioRecordTool(BaseTool):
    """Retrieve a single iDigBio specimen record by UUID."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("fields", {}).get("timeout", 30)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        uuid = (arguments.get("uuid") or "").strip()
        if not uuid:
            return {"status": "error", "error": "'uuid' is required"}

        try:
            resp = requests.get(
                f"{IDIGBIO_BASE}/view/records/{uuid}",
                headers={"Accept": "application/json"},
                timeout=self.timeout,
            )
            if resp.status_code == 404:
                return {
                    "status": "success",
                    "data": {},
                    "metadata": {
                        "query_uuid": uuid,
                        "note": f"No iDigBio record '{uuid}'.",
                    },
                }
            resp.raise_for_status()
            rec = resp.json()
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"iDigBio request timed out after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"iDigBio request failed: {e}"}
        except ValueError:
            return {"status": "error", "error": "iDigBio returned a non-JSON response"}

        if not isinstance(rec, dict) or not rec.get("uuid"):
            return {"status": "success", "data": {}, "metadata": {"query_uuid": uuid}}
        summary = _summarize(rec)
        summary["data"] = rec.get("data", {})  # full Darwin Core record
        return {
            "status": "success",
            "data": summary,
            "metadata": {"query_uuid": uuid, "source": "iDigBio"},
        }
