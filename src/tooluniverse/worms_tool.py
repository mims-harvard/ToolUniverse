import requests
import urllib.parse
from typing import Any, Dict
from .base_tool import BaseTool
from .tool_registry import register_tool


# AphiaID-keyed enrichment operations. Each maps a `fields.operation` value to the
# WoRMS REST path that takes a single {AphiaID} path parameter and returns JSON.
_APHIA_OPERATIONS = {
    "classification": "AphiaClassificationByAphiaID",
    "vernaculars": "AphiaVernacularsByAphiaID",
    "distributions": "AphiaDistributionsByAphiaID",
    "synonyms": "AphiaSynonymsByAphiaID",
}


@register_tool("WoRMSRESTTool")
class WoRMSRESTTool(BaseTool):
    # Maximum number of records WoRMS returns from a single AphiaRecordsByName call.
    _PAGE_SIZE = 50

    def __init__(self, tool_config: Dict):
        super().__init__(tool_config)
        self.base_url = "https://www.marinespecies.org/rest"
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        self.timeout = 30

    def _operation(self) -> str:
        return self.tool_config.get("fields", {}).get("operation", "search_by_name")

    def _run_aphia_operation(
        self, operation: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve an AphiaID to an enrichment resource (classification, vernaculars,
        distributions, synonyms). Returns the standard envelope and never raises."""
        aphia_id = arguments.get("AphiaID")
        if isinstance(aphia_id, bool) or not isinstance(aphia_id, int) or aphia_id < 1:
            return {
                "status": "error",
                "error": "AphiaID must be a positive integer",
                "parameter": "AphiaID",
            }

        path = _APHIA_OPERATIONS[operation]
        if operation == "synonyms":
            return self._run_synonyms(path, aphia_id, arguments)
        url = f"{self.base_url}/{path}/{aphia_id}"
        try:
            response = self.session.get(url, timeout=self.timeout)
            # WoRMS returns HTTP 204 (no content) when a taxon has no records for
            # this resource. Treat that as a successful empty result.
            if response.status_code == 204 or not response.text.strip():
                empty = {} if operation == "classification" else []
                return {
                    "status": "success",
                    "data": empty,
                    "url": url,
                    "message": f"No {operation} records for AphiaID {aphia_id}",
                }
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            return {"status": "error", "error": f"WoRMS API error: {str(e)}"}

        result = {"status": "success", "data": data, "url": url, "AphiaID": aphia_id}
        if isinstance(data, list):
            result["count"] = len(data)
        return result

    @staticmethod
    def _parse_bool_filter(arguments: Dict[str, Any], key: str):
        """Read an optional boolean search filter (`marine_only`, `like`, ...).

        Returns ``(value, error)`` where ``value`` is ``None`` when the caller
        did not set the parameter, so the request can be sent exactly as it was
        before this parameter existed.
        """
        raw = arguments.get(key)
        if key not in arguments or raw is None:
            return None, None
        if isinstance(raw, bool):
            return raw, None
        if isinstance(raw, str) and raw.strip().lower() in ("true", "false"):
            return raw.strip().lower() == "true", None
        return None, f"{key} must be a boolean, got: {raw!r}"

    @classmethod
    def _parse_marine_only(cls, arguments: Dict[str, Any]):
        """Read the optional `marine_only` argument (see `_parse_bool_filter`)."""
        return cls._parse_bool_filter(arguments, "marine_only")

    def _run_synonyms(
        self, path: str, aphia_id: int, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Page through the official 50-record synonym endpoint."""
        controls = self._pagination_controls(arguments, default_limit=50)
        if isinstance(controls, dict):
            return controls
        limit, offset = controls
        base_url = f"{self.base_url}/{path}/{aphia_id}"
        records = []
        page_offset = offset
        while len(records) <= limit:
            url = f"{base_url}?offset={page_offset}"
            try:
                response = self.session.get(url, timeout=self.timeout)
                if response.status_code == 204 or not response.text.strip():
                    break
                response.raise_for_status()
                page = response.json()
            except Exception as exc:
                return {"status": "error", "error": f"WoRMS API error: {exc}"}
            if not isinstance(page, list) or not page:
                break
            records.extend(page)
            if len(page) < self._PAGE_SIZE:
                break
            page_offset += self._PAGE_SIZE

        returned = records[:limit]
        has_more = len(records) > limit
        return {
            "status": "success",
            "data": returned,
            "url": f"{base_url}?offset={offset}",
            "AphiaID": aphia_id,
            "count": len(returned),
            "offset": offset,
            "limit": limit,
            "has_more": has_more,
            "next_offset": offset + len(returned) if has_more else None,
            "truncated": has_more or offset > 1,
            "result_set_complete": offset == 1 and not has_more,
        }

    @staticmethod
    def _pagination_controls(arguments: Dict[str, Any], default_limit: int):
        limit = arguments.get("limit", default_limit)
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= 1000
        ):
            return {
                "status": "error",
                "error": "limit must be an integer between 1 and 1000",
                "parameter": "limit",
            }
        offset = arguments.get("offset", 1)
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 1:
            return {
                "status": "error",
                "error": "offset must be a positive integer",
                "parameter": "offset",
            }
        return limit, offset

    def _run_search_by_name(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = arguments.get("query")
        if not isinstance(query, str) or not query.strip():
            return {
                "status": "error",
                "error": "query must be a non-empty string",
                "parameter": "query",
            }
        controls = self._pagination_controls(arguments, default_limit=20)
        if isinstance(controls, dict):
            return controls
        limit, offset = controls

        # WoRMS applies `like=true`, `marine_only=true` and `extant_only=true`
        # on AphiaRecordsByName unless told otherwise, so records flagged only
        # freshwater/terrestrial (e.g. the parasite Schistosoma mansoni,
        # AphiaID 1599676) are filtered out upstream. Send a filter only when
        # the caller set it explicitly: callers who omit them keep
        # byte-identical requests and result sets.
        sent_filters = {}
        filters = {}
        for key in ("like", "marine_only", "extant_only"):
            value, error = self._parse_bool_filter(arguments, key)
            if error:
                return {"status": "error", "error": error, "parameter": key}
            if value is not None:
                sent_filters[key] = str(value).lower()
            filters[key] = True if value is None else value
        filter_suffix = (
            "&" + urllib.parse.urlencode(sent_filters) if sent_filters else ""
        )
        effective_marine_only = filters["marine_only"]

        query = query.strip()
        encoded_query = urllib.parse.quote(query, safe="")
        base_url = f"{self.base_url}/AphiaRecordsByName/{encoded_query}"
        first_url = f"{base_url}?offset={offset}{filter_suffix}"

        # WoRMS caps every AphiaRecordsByName response at _PAGE_SIZE records and
        # pages with a 1-based `offset`. Walk pages until the caller's `limit` is
        # satisfied, fetching one record beyond it so `has_more` can be reported
        # without enumerating the entire result set.
        records: list = []
        page_offset = offset
        while len(records) <= limit:
            url = f"{base_url}?offset={page_offset}{filter_suffix}"
            try:
                response = self.session.get(url, timeout=self.timeout)
                # 204 / empty body = no (further) records for this query.
                if response.status_code == 204 or not response.text.strip():
                    break
                response.raise_for_status()
                page = response.json()
            except Exception as e:
                return {"status": "error", "error": f"WoRMS API error: {str(e)}"}
            if not isinstance(page, list) or not page:
                break
            records.extend(page)
            if len(page) < self._PAGE_SIZE:
                break
            page_offset += self._PAGE_SIZE

        if not records:
            message = "No results found for this query"
            if effective_marine_only:
                # An empty page under the upstream marine filter is ambiguous:
                # the name may be unknown to WoRMS, or known but non-marine.
                # Say so instead of reporting a confident "not found".
                message += (
                    ". Note that WoRMS restricted this search to marine taxa "
                    "(marine_only defaults to true), so species recorded only "
                    "as freshwater or terrestrial are excluded. Retry with "
                    "marine_only=false to include freshwater/terrestrial "
                    "species."
                )
            return {
                "status": "success",
                "data": [],
                "url": first_url,
                "count": 0,
                "offset": offset,
                "limit": limit,
                "marine_only": effective_marine_only,
                "has_more": False,
                "next_offset": None,
                "truncated": offset > 1,
                "result_set_complete": offset == 1,
                **filters,
                "message": message,
            }

        has_more = len(records) > limit
        page = records[:limit]
        return {
            "status": "success",
            "data": page,
            "url": first_url,
            "count": len(page),
            "offset": offset,
            "limit": limit,
            "marine_only": effective_marine_only,
            "has_more": has_more,
            "next_offset": offset + len(page) if has_more else None,
            "truncated": has_more or offset > 1,
            "result_set_complete": offset == 1 and not has_more,
            **filters,
        }

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        operation = self._operation()
        if operation in _APHIA_OPERATIONS:
            return self._run_aphia_operation(operation, arguments)
        return self._run_search_by_name(arguments)
