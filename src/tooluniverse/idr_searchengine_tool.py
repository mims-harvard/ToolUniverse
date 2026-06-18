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

        payload, err = self._get(f"{resource}/search/", params)
        if err is not None:
            return {"status": "error", "error": err}

        rows = self._unwrap_results(payload)

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
                "containers": containers,
            }
        else:
            limit = args.get("max_results")
            if isinstance(limit, int) and limit > 0:
                rows = rows[:limit]
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
                "images": images,
            }
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
        values = [
            {
                "value": r.get("Value"),
                "image_count": r.get("Number of images"),
            }
            for r in rows
            if isinstance(r, dict)
        ]
        limit = args.get("max_results")
        if isinstance(limit, int) and limit > 0:
            values = values[:limit]
        return {
            "status": "success",
            "data": {
                "resource": resource,
                "key": key,
                "value_count": len(values),
                "values": values,
            },
        }
