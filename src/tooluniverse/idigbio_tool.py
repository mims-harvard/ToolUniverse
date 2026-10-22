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


def _media_summary(item: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten an iDigBio media (image) record to the most useful fields."""
    data = item.get("data", {}) or {}
    idx = item.get("indexTerms", {}) or {}
    return {
        "uuid": item.get("uuid"),
        "type": data.get("dcterms:type") or idx.get("type"),
        "format": data.get("dcterms:format") or idx.get("format"),
        "provider_managed_id": data.get("ac:providerManagedID"),
        "creator": data.get("dc:creator"),
        "rights_owner": data.get("xmpRights:Owner"),
        "usage_terms": data.get("xmpRights:UsageTerms"),
        "access_uri": data.get("ac:accessURI") or data.get("ac:goodQualityAccessURI"),
        "records": item.get("records") or idx.get("records"),
    }


def _build_rq(arguments: Dict[str, Any]) -> Dict[str, str]:
    """Build the iDigBio Darwin-Core query (rq) from per-field args or a raw rq."""
    raw = arguments.get("rq")
    if isinstance(raw, dict) and raw:
        return {k: v for k, v in raw.items() if v is not None}
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict) and parsed:
                return parsed
        except (ValueError, TypeError):
            pass
    return {
        f: arguments[f].strip()
        for f in _QUERY_FIELDS
        if isinstance(arguments.get(f), str) and arguments[f].strip()
    }


def _idigbio_get(url: str, params: Dict[str, Any], timeout: int):
    """GET an iDigBio endpoint, returning (payload, error_envelope).

    Exactly one of the two is non-None; the error envelope is the standard
    {"status": "error", ...} dict so callers never raise.
    """
    try:
        resp = requests.get(
            url,
            params=params,
            headers={"Accept": "application/json"},
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json(), None
    except requests.exceptions.Timeout:
        return None, {
            "status": "error",
            "error": f"iDigBio request timed out after {timeout}s",
        }
    except requests.exceptions.RequestException as e:
        return None, {"status": "error", "error": f"iDigBio request failed: {e}"}
    except ValueError:
        return None, {
            "status": "error",
            "error": "iDigBio returned a non-JSON response",
        }


@register_tool("iDigBioSearchTool")
class iDigBioSearchTool(BaseTool):
    """Search iDigBio specimen records (records / media) and summary facets.

    Dispatch is driven by ``fields.mode``:
      - unset / "records" : /search/records/ specimen occurrence records (default)
      - "media"           : /search/media/ specimen image/media records
      - "summary"         : /summary/top/records/ facet counts + /summary/count/
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("fields", {}).get("timeout", 30)
        self.mode = tool_config.get("fields", {}).get("mode", "records")

    @staticmethod
    def _pagination(arguments: Dict[str, Any]):
        limit = arguments.get("limit", 10)
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            return None, None, {
                "status": "error",
                "error": "limit must be an integer between 1 and 100",
                "parameter": "limit",
            }
        offset = arguments.get("offset", 0)
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            return None, None, {
                "status": "error",
                "error": "offset must be a non-negative integer",
                "parameter": "offset",
            }
        return limit, offset, None

    @staticmethod
    def _search_result(payload: Any, rq: Dict[str, Any], limit: int, offset: int, summarizer):
        if not isinstance(payload, dict) or not isinstance(payload.get("items", []), list):
            return {
                "status": "error",
                "error": "iDigBio returned an unexpected search payload",
            }
        items = payload.get("items", []) or []
        data = [summarizer(it) for it in items if isinstance(it, dict)]
        total = payload.get("itemCount")
        total_is_exact = isinstance(total, int) and not isinstance(total, bool) and total >= 0
        if not total_is_exact:
            total = None
        has_more = offset + len(items) < total if total_is_exact else None
        truncated = offset > 0 or has_more is True or not total_is_exact
        return {
            "status": "success",
            "data": data,
            "metadata": {
                "total_available": total,
                "total_available_is_exact": total_is_exact,
                "returned": len(data),
                "limit": limit,
                "offset": offset,
                "has_more": has_more,
                "next_offset": offset + len(items) if has_more else None,
                "truncated": truncated,
                "result_set_complete": not truncated,
                "query": rq,
                "source": "iDigBio",
            },
        }

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if self.mode == "summary":
            return self._run_summary(arguments)
        if self.mode == "media":
            return self._run_media(arguments)
        return self._run_records(arguments)

    def _run_records(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        rq = _build_rq(arguments)
        if not rq:
            return {
                "status": "error",
                "error": "Provide at least one query field: "
                + ", ".join(_QUERY_FIELDS),
            }
        limit, offset, pagination_error = self._pagination(arguments)
        if pagination_error is not None:
            return pagination_error
        params = {"rq": json.dumps(rq), "limit": limit, "offset": offset}
        payload, err = _idigbio_get(
            f"{IDIGBIO_BASE}/search/records/", params, self.timeout
        )
        if err is not None:
            return err
        return self._search_result(payload, rq, limit, offset, _summarize)

    def _run_media(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        rq = _build_rq(arguments)
        if not rq:
            return {
                "status": "error",
                "error": "Provide at least one query field (e.g. scientificname, "
                "genus, family) or an rq query.",
            }
        limit, offset, pagination_error = self._pagination(arguments)
        if pagination_error is not None:
            return pagination_error
        params = {"rq": json.dumps(rq), "limit": limit, "offset": offset}
        payload, err = _idigbio_get(
            f"{IDIGBIO_BASE}/search/media/", params, self.timeout
        )
        if err is not None:
            return err
        return self._search_result(payload, rq, limit, offset, _media_summary)

    def _run_summary(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        rq = _build_rq(arguments)
        if not rq:
            return {
                "status": "error",
                "error": "Provide at least one query field (e.g. scientificname, "
                "genus, family) or an rq query.",
            }
        rq_json = json.dumps(rq)

        # Always return the exact total count for the query.
        count_payload, err = _idigbio_get(
            f"{IDIGBIO_BASE}/summary/count/records/",
            {"rq": rq_json},
            self.timeout,
        )
        if err is not None:
            return err
        total = (count_payload or {}).get("itemCount")

        facets: Dict[str, Any] = {}
        top_fields = arguments.get("top_fields")
        if isinstance(top_fields, list):
            top_fields = ",".join(str(f) for f in top_fields if f)
        if isinstance(top_fields, str) and top_fields.strip():
            try:
                count = max(1, min(int(arguments.get("count") or 10), 100))
            except (TypeError, ValueError):
                count = 10
            top_payload, err = _idigbio_get(
                f"{IDIGBIO_BASE}/summary/top/records/",
                {"rq": rq_json, "top_fields": top_fields.strip(), "count": count},
                self.timeout,
            )
            if err is not None:
                return err
            facets = {
                k: v
                for k, v in (top_payload or {}).items()
                if k != "itemCount" and isinstance(v, dict)
            }

        return {
            "status": "success",
            "data": {"itemCount": total, "facets": facets},
            "metadata": {
                "query": rq,
                "top_fields": top_fields if isinstance(top_fields, str) else None,
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
