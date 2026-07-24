"""
GBIF Backbone Taxonomy Navigation Tool

Provides programmatic navigation of the GBIF (Global Biodiversity Information
Facility) Backbone Taxonomy tree and scientific-name parsing via the public
GBIF REST API (https://api.gbif.org/v1/). No API key is required.

This tool complements the existing GBIF species/occurrence tools (which cover
keyword search, name matching, species detail, suggestion and occurrence
statistics) by exposing the taxonomic-tree navigation and name-parsing
endpoints that were previously unwrapped:

- GBIF_get_taxon_children      GET /species/{key}/children
- GBIF_get_taxon_parents       GET /species/{key}/parents
- GBIF_get_taxon_synonyms      GET /species/{key}/synonyms
- GBIF_get_vernacular_names    GET /species/{key}/vernacularNames
- GBIF_parse_name              POST /parser/name

A taxonKey/usageKey can be obtained from the existing GBIF_match_name or
GBIF_search_species tools (e.g. Panthera leo -> 5219404).

API Base: https://api.gbif.org/v1
Authentication: none (public, no key).
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

GBIF_API_BASE = "https://api.gbif.org/v1"


def _http_get(url: str, params: Dict[str, Any], timeout: int):
    """GET helper. Returns (ok, payload_or_error_string, status_code)."""
    try:
        resp = requests.get(
            url,
            params=params,
            headers={"Accept": "application/json"},
            timeout=timeout,
        )
    except requests.exceptions.Timeout:
        return False, "GBIF request timed out", None
    except requests.exceptions.RequestException as exc:
        return False, "GBIF request failed: " + str(exc), None
    if resp.status_code != 200:
        snippet = (resp.text or "").strip()[:200]
        return (
            False,
            "GBIF returned HTTP " + str(resp.status_code) + ": " + snippet,
            resp.status_code,
        )
    try:
        return True, resp.json(), resp.status_code
    except ValueError:
        return False, "GBIF returned a non-JSON response", resp.status_code


def _http_post_json(url: str, body: Any, timeout: int):
    """POST JSON helper. Returns (ok, payload_or_error_string, status_code)."""
    try:
        resp = requests.post(
            url,
            json=body,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=timeout,
        )
    except requests.exceptions.Timeout:
        return False, "GBIF request timed out", None
    except requests.exceptions.RequestException as exc:
        return False, "GBIF request failed: " + str(exc), None
    # GBIF name parser returns 201 (Created) on success, also accept 200.
    if resp.status_code not in (200, 201):
        snippet = (resp.text or "").strip()[:200]
        return (
            False,
            "GBIF returned HTTP " + str(resp.status_code) + ": " + snippet,
            resp.status_code,
        )
    try:
        return True, resp.json(), resp.status_code
    except ValueError:
        return False, "GBIF returned a non-JSON response", resp.status_code


def _slim_usage(rec: Dict[str, Any]) -> Dict[str, Any]:
    """Project a GBIF name-usage record onto a stable, useful subset of fields."""
    keys = [
        "key",
        "scientificName",
        "canonicalName",
        "authorship",
        "rank",
        "taxonomicStatus",
        "kingdom",
        "phylum",
        "class",
        "order",
        "family",
        "genus",
        "species",
        "parentKey",
        "acceptedKey",
        "accepted",
        "numDescendants",
    ]
    return {k: rec.get(k) for k in keys}


def _slim_vernacular(rec: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "vernacularName": rec.get("vernacularName"),
        "language": rec.get("language"),
        "country": rec.get("country"),
        "source": rec.get("source"),
    }


def _slim_parsed(rec: Dict[str, Any]) -> Dict[str, Any]:
    keys = [
        "scientificName",
        "type",
        "canonicalName",
        "canonicalNameComplete",
        "genusOrAbove",
        "specificEpithet",
        "infraSpecificEpithet",
        "rankMarker",
        "authorship",
        "bracketAuthorship",
        "year",
        "parsed",
        "parsedPartially",
    ]
    return {k: rec.get(k) for k in keys}


@register_tool("GBIFTaxonomyTool")
class GBIFTaxonomyTool(BaseTool):
    """
    Navigate the GBIF Backbone Taxonomy tree and parse scientific names.

    Operations (selected via the ``operation`` argument):
      - get_children        Direct child taxa of a taxonKey (paged)
      - get_parents         Full ranked ancestor lineage of a taxonKey
      - get_synonyms        Taxonomic synonyms of a taxonKey (paged)
      - get_vernacular_names Common (vernacular) names of a taxonKey (paged)
      - parse_name          Parse scientific name string(s) into components

    Get a taxonKey first from GBIF_match_name or GBIF_search_species.
    No API key required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {}) or {}
        # operation may be fixed by the JSON config (one tool per operation)
        self.fixed_operation = fields.get("operation")
        self.base_url = fields.get("base_url", GBIF_API_BASE).rstrip("/")

    # ------------------------------------------------------------------ #
    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            return {"status": "error", "error": "arguments must be an object"}
        operation = self.fixed_operation or arguments.get("operation")
        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        dispatch = {
            "get_children": self._get_paged_usages,
            "get_synonyms": self._get_paged_usages,
            "get_parents": self._get_parents,
            "get_vernacular_names": self._get_vernacular_names,
            "parse_name": self._parse_name,
        }
        handler = dispatch.get(operation)
        if handler is None:
            return {
                "status": "error",
                "error": "Unknown operation '"
                + str(operation)
                + "'. Valid: get_children, get_parents, get_synonyms, "
                + "get_vernacular_names, parse_name",
            }
        # the paged-usages handler needs to know which sub-endpoint to hit
        if operation in ("get_children", "get_synonyms"):
            return handler(arguments, operation.replace("get_", ""))
        return handler(arguments)

    # ------------------------------------------------------------------ #
    def _resolve_key(self, arguments: Dict[str, Any]):
        """Return (key:int, error_response_or_None)."""
        raw = arguments.get(
            "taxon_key", arguments.get("taxonKey", arguments.get("key"))
        )
        if raw is None:
            return None, {
                "status": "error",
                "error": "Missing required parameter: taxon_key",
            }
        try:
            return int(raw), None
        except (TypeError, ValueError):
            return None, {
                "status": "error",
                "error": "taxon_key must be an integer GBIF usageKey (e.g. 5219404 for Panthera leo)",
            }

    def _limit(self, arguments: Dict[str, Any]) -> int:
        try:
            n = int(arguments.get("limit", 20))
        except (TypeError, ValueError):
            return 20
        return max(1, min(n, 100))

    # ------------------------------------------------------------------ #
    def _get_paged_usages(self, arguments: Dict[str, Any], sub: str) -> Dict[str, Any]:
        """children / synonyms: GET /species/{key}/{sub} -> paged usage list."""
        key, err = self._resolve_key(arguments)
        if err:
            return err
        limit = self._limit(arguments)
        url = self.base_url + "/species/" + str(key) + "/" + sub
        ok, payload, _ = _http_get(url, {"limit": limit, "offset": 0}, self.timeout)
        if not ok:
            return {"status": "error", "error": payload}
        results = payload.get("results", []) if isinstance(payload, dict) else []
        data = [_slim_usage(r) for r in results]
        return {
            "status": "success",
            "data": data,
            "metadata": {
                "taxon_key": key,
                "endpoint": "species/" + str(key) + "/" + sub,
                "returned": len(data),
                "end_of_records": payload.get("endOfRecords")
                if isinstance(payload, dict)
                else None,
            },
        }

    def _get_parents(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """GET /species/{key}/parents -> bare JSON array, root-first lineage."""
        key, err = self._resolve_key(arguments)
        if err:
            return err
        url = self.base_url + "/species/" + str(key) + "/parents"
        ok, payload, _ = _http_get(url, {}, self.timeout)
        if not ok:
            return {"status": "error", "error": payload}
        records = payload if isinstance(payload, list) else []
        data = [_slim_usage(r) for r in records]
        return {
            "status": "success",
            "data": data,
            "metadata": {
                "taxon_key": key,
                "endpoint": "species/" + str(key) + "/parents",
                "returned": len(data),
                "note": "Ordered root-first (KINGDOM -> ... -> immediate parent).",
            },
        }

    def _get_vernacular_names(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """GET /species/{key}/vernacularNames -> paged. Optional language filter."""
        key, err = self._resolve_key(arguments)
        if err:
            return err
        lang = arguments.get("language")
        if lang is not None:
            lang = str(lang).strip().lower() or None
        url = self.base_url + "/species/" + str(key) + "/vernacularNames"
        ok, payload, _ = _http_get(url, {"limit": 100, "offset": 0}, self.timeout)
        if not ok:
            return {"status": "error", "error": payload}
        results = payload.get("results", []) if isinstance(payload, dict) else []
        if lang:
            results = [r for r in results if (r.get("language") or "").lower() == lang]
        # de-duplicate on (name, language) preserving order
        seen = set()
        data = []
        for r in results:
            slim = _slim_vernacular(r)
            sig = (slim["vernacularName"], slim["language"])
            if sig in seen:
                continue
            seen.add(sig)
            data.append(slim)
        return {
            "status": "success",
            "data": data,
            "metadata": {
                "taxon_key": key,
                "endpoint": "species/" + str(key) + "/vernacularNames",
                "language_filter": lang,
                "returned": len(data),
            },
        }

    def _parse_name(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """POST /parser/name with a JSON array of name strings."""
        names = arguments.get("names", arguments.get("name"))
        if names is None:
            return {
                "status": "error",
                "error": "Missing required parameter: name (or names)",
            }
        if isinstance(names, str):
            names = [names]
        if not isinstance(names, list) or not names:
            return {
                "status": "error",
                "error": "name/names must be a non-empty string or list of strings",
            }
        names = [str(n) for n in names if str(n).strip()]
        if not names:
            return {"status": "error", "error": "No non-empty names supplied"}
        url = self.base_url + "/parser/name"
        ok, payload, _ = _http_post_json(url, names, self.timeout)
        if not ok:
            return {"status": "error", "error": payload}
        records = payload if isinstance(payload, list) else [payload]
        data = [_slim_parsed(r) for r in records if isinstance(r, dict)]
        return {
            "status": "success",
            "data": data,
            "metadata": {
                "endpoint": "parser/name",
                "input_count": len(names),
                "returned": len(data),
            },
        }
