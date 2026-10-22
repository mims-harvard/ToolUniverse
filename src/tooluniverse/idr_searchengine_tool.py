"""
IDR Search Engine Tool

Cross-study metadata search for the Image Data Resource (IDR,
https://idr.openmicroscopy.org), the public repository of reference
bioimaging datasets from published studies.

The existing IDR_* tools (idr_tools.json) walk the OMERO project tree
(projects -> datasets -> images -> map annotations). They cannot answer the
most common research question -- "which IDR images / screens / projects
involve gene X (or organism Y, compound Z, phenotype W)?" -- because that
requires a search across every study at once.

This tool wraps the IDR "searchengine" Elasticsearch-backed API
(https://idr.openmicroscopy.org/searchengine/api/v1/resources/) which indexes
the curated key/value metadata of every IDR image and exposes:

  * IDR_search_images        -- images matching a metadata key/value
  * IDR_search_studies       -- the screens / projects that contain matches
  * IDR_list_metadata_keys   -- the available metadata attribute names
  * IDR_list_values_for_key  -- every value (and image count) for one key

No API key. Public, anonymous access. Read-only.
"""

import requests
from typing import Any, Dict, List
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("IDRSearchEngineTool")
class IDRSearchEngineTool(BaseTool):
    """Cross-study metadata search over the Image Data Resource (IDR)."""

    SEARCH_BASE = "https://idr.openmicroscopy.org/searchengine/api/v1/resources"

    def __init__(self, tool_config: Dict):
        super().__init__(tool_config)
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": "ToolUniverse/1.0 (IDR searchengine client)",
            }
        )
        self.timeout = 30

    # ------------------------------------------------------------------ #
    # Dispatch
    # ------------------------------------------------------------------ #
    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        tool_name = self.tool_config.get("name", "")
        try:
            if tool_name == "IDR_search_images":
                return self._search(arguments, return_containers=False)
            if tool_name == "IDR_search_studies":
                return self._search(arguments, return_containers=True)
            if tool_name == "IDR_list_metadata_keys":
                return self._list_keys(arguments)
            if tool_name == "IDR_list_values_for_key":
                return self._list_values_for_key(arguments)
            return {"status": "error", "error": f"Unknown tool: {tool_name}"}
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": "IDR searchengine request timed out after 30s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"IDR searchengine API error: {e}"}
        except Exception as e:  # never raise
            return {"status": "error", "error": f"Unexpected error: {e}"}

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _get(self, path: str, params: Dict[str, Any]):
        """GET against the searchengine, returning (json_or_None, error_str)."""
        url = f"{self.SEARCH_BASE}/{path}"
        resp = self.session.get(url, params=params, timeout=self.timeout)
        if resp.status_code != 200:
            return None, f"HTTP {resp.status_code}: {resp.text[:200]}"
        try:
            payload = resp.json()
        except ValueError:
            return None, f"Non-JSON response: {resp.text[:200]}"
        # The searchengine ALWAYS returns an "Error" key (HTTP 200). It is the
        # literal string "none" (or null) on success, and a real message on a
        # validation/input error -- so treat "none"/"null"/empty as no error.
        if isinstance(payload, dict):
            err = payload.get("Error")
            if err and str(err).strip().lower() not in ("none", "null", ""):
                return None, str(err)
        return payload, None

    @staticmethod
    def _unwrap_results(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """The searchengine 'results' field is polymorphic.

        * plain image search  -> results is a list of image rows
        * return_containers   -> results is {"results": [...containers...]}
        * no matches          -> results is [] (an empty list)
        """
        results = payload.get("results")
        if isinstance(results, dict):
            inner = results.get("results", [])
            return inner if isinstance(inner, list) else []
        if isinstance(results, list):
            return results
        return []

    @staticmethod
    def _search_page(payload: Dict[str, Any]):
        """Return one searchengine page plus its global count and cursor.

        IDR nests image search rows under ``results.results`` and exposes an
        Elasticsearch ``bookmark`` for the next 1000-row server page.  Older
        responses can still contain a plain list, so keep that form working.
        """
        result_block = payload.get("results") if isinstance(payload, dict) else None
        if isinstance(result_block, dict):
            rows = result_block.get("results", [])
            rows = rows if isinstance(rows, list) else []
            total = result_block.get("size")
            if not isinstance(total, int) or total < 0:
                total = len(rows)
            bookmark = result_block.get("bookmark")
            if isinstance(bookmark, list) and len(bookmark) == 1:
                bookmark = bookmark[0]
            return rows, total, bookmark
        rows = result_block if isinstance(result_block, list) else []
        return rows, len(rows), None

    @staticmethod
    def _pagination_args(args: Dict[str, Any], default_limit: int | None):
        offset = args.get("offset", 0)
        limit = args.get("max_results", default_limit)
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            return None, None, "Parameter 'offset' must be a non-negative integer."
        if limit is not None and (
            isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0
        ):
            return None, None, "Parameter 'max_results' must be a positive integer."
        return offset, limit, None

    @staticmethod
    def _kv_pairs(row: Dict[str, Any]) -> List[Dict[str, str]]:
        """Flatten an image/container key_values list to simple name/value dicts."""
        out = []
        for kv in row.get("key_values", []) or []:
            if not isinstance(kv, dict):
                continue
            name = kv.get("name", kv.get("key", ""))
            out.append({"name": str(name), "value": str(kv.get("value", ""))})
        return out

    # ------------------------------------------------------------------ #
    # Operations
    # ------------------------------------------------------------------ #
    def _search(self, args: Dict[str, Any], return_containers: bool) -> Dict[str, Any]:
        value = args.get("value")
        if value is None or str(value).strip() == "":
            return {
                "status": "error",
                "error": "Parameter 'value' is required and must be non-empty.",
            }
        resource = args.get("resource") or "image"
        params: Dict[str, Any] = {
            "value": value,
            "operator": args.get("operator") or "equals",
        }
        # The searchengine's case_sensitive parameter misbehaves when sent
        # explicitly (case_sensitive=false yields zero hits), so only send it
        # when the caller actively requests case-sensitive matching; otherwise
        # rely on the server default, which matches case-insensitively.
        if args.get("case_sensitive"):
            params["case_sensitive"] = "true"
        if args.get("key"):
            params["key"] = args["key"]
        if args.get("study"):
            params["study"] = args["study"]
        if return_containers:
            params["return_containers"] = "true"

        # The API server page is fixed at 1000 rows.  Its response includes a
        # global ``size`` and a bookmark cursor, both of which used to be
        # discarded by this wrapper.  Walk only as many server pages as needed
        # to satisfy a global client-side offset/limit.
        offset, limit, pagination_error = self._pagination_args(args, 1000)
        if pagination_error:
            return {"status": "error", "error": pagination_error}

        rows: List[Dict[str, Any]] = []
        total = 0
        remaining_skip = offset
        bookmark = None
        seen_bookmarks = set()
        while len(rows) < limit:
            page_params = dict(params)
            if bookmark is not None:
                page_params["bookmark"] = bookmark
            payload, err = self._get(f"{resource}/search/", page_params)
            if err is not None:
                return {"status": "error", "error": err}
            page_rows, total, next_bookmark = self._search_page(payload)
            if remaining_skip >= len(page_rows):
                remaining_skip -= len(page_rows)
                page_rows = []
            else:
                page_rows = page_rows[remaining_skip:]
                remaining_skip = 0
            rows.extend(page_rows[: limit - len(rows)])
            if len(rows) >= limit or offset + len(rows) >= total:
                break
            if next_bookmark is None or next_bookmark in seen_bookmarks:
                break
            seen_bookmarks.add(next_bookmark)
            bookmark = next_bookmark

        query = {
            "key": args.get("key"),
            "value": str(value),
            "operator": params["operator"],
        }

        if return_containers:
            containers = [
                {
                    "id": r.get("id"),
                    "name": r.get("name"),
                    "type": r.get("type"),
                    "image_count": r.get("image count"),
                    "key_values": self._kv_pairs(r),
                }
                for r in rows
            ]
            data = {
                "query": query,
                "container_count": len(containers),
                "total_container_count": total,
                "containers": containers,
            }
        else:
            images = [
                {
                    "image_id": r.get("id"),
                    "name": r.get("name"),
                    "image_webclient_url": r.get("image_webclient_url"),
                    # IDR image rows carry the study under screen_name/project_name.
                    "study": r.get("screen_name") or r.get("project_name"),
                    "dataset_name": r.get("dataset_name"),
                    "key_values": self._kv_pairs(r),
                }
                for r in rows
            ]
            data = {
                "query": query,
                "image_count": len(images),
                "total_image_count": total,
                "images": images,
            }
        returned = len(rows)
        has_more = offset + returned < total
        data.update(
            {
                "offset": offset,
                "limit": limit,
                "returned": returned,
                "has_more": has_more,
                "next_offset": offset + returned if has_more else None,
                "result_set_complete": offset == 0 and returned == total,
            }
        )
        return {"status": "success", "data": data}

    def _list_keys(self, args: Dict[str, Any]) -> Dict[str, Any]:
        resource = args.get("resource") or "image"
        payload, err = self._get(f"{resource}/keys/", {})
        if err is not None:
            return {"status": "error", "error": err}
        # payload is a list of {"data_source": ..., "<resource>": [keys...]}
        keys: List[str] = []
        if isinstance(payload, list):
            for block in payload:
                if isinstance(block, dict):
                    candidate = block.get(resource)
                    if isinstance(candidate, list):
                        for k in candidate:
                            if k not in keys:
                                keys.append(str(k))
        return {
            "status": "success",
            "data": {"resource": resource, "key_count": len(keys), "keys": keys},
        }

    def _list_values_for_key(self, args: Dict[str, Any]) -> Dict[str, Any]:
        key = args.get("key")
        if not key:
            return {"status": "error", "error": "Parameter 'key' is required."}
        resource = args.get("resource") or "image"
        payload, err = self._get(f"{resource}/searchvaluesusingkey/", {"key": key})
        if err is not None:
            return {"status": "error", "error": err}
        rows = payload.get("data", []) if isinstance(payload, dict) else []
        all_values = [
            {
                "value": r.get("Value"),
                "image_count": r.get("Number of images"),
            }
            for r in rows
            if isinstance(r, dict)
        ]
        offset, limit, pagination_error = self._pagination_args(args, None)
        if pagination_error:
            return {"status": "error", "error": pagination_error}
        total = len(all_values)
        end = None if limit is None else offset + limit
        values = all_values[offset:end]
        has_more = offset + len(values) < total
        return {
            "status": "success",
            "data": {
                "resource": resource,
                "key": key,
                "value_count": len(values),
                "total_value_count": total,
                "values": values,
                "offset": offset,
                "limit": limit,
                "returned": len(values),
                "has_more": has_more,
                "next_offset": offset + len(values) if has_more else None,
                "result_set_complete": offset == 0 and len(values) == total,
            },
        }
