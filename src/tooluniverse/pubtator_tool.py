from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

# Official REST root  (cf. NIH “entity autocomplete” & “search” examples)
BASE_URL = "https://www.ncbi.nlm.nih.gov/research/pubtator3-api"
CONFIG_FILE = Path(__file__).with_name("pubtator_tool_config.json")


@register_tool("PubTatorTool")
class PubTatorTool(BaseTool):
    """Generic wrapper around a single PubTator 3 endpoint supporting JSON-defined configs."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self._method: str = tool_config.get("method", "GET").upper()
        self._path: str = tool_config["endpoint_path"]
        self._param_map: Dict[str, str] = tool_config.get("param_map", {})
        self._body_param: Optional[str] = tool_config.get("body_param")
        self._id_in_path_key: Optional[str] = tool_config.get("id_in_path")

        fields = tool_config.get("fields", {})
        if "body_param" in fields:
            self._body_param = fields["body_param"]
        self._tool_subtype: str = fields.get("tool_subtype", "")

    # ------------------------------------------------------------------ public API --------------
    def run(self, arguments: Dict[str, Any]):
        args = arguments.copy()
        # Pop limit early so it doesn't leak to the API as a query param.
        # The PubTator3 search API ignores the page_size param and always
        # returns 10 results per page, so we apply client-side truncation.
        _limit = args.pop("limit", None)
        if _limit is not None:
            try:
                _limit = int(_limit)
            except (TypeError, ValueError):
                _limit = None

        # Special case for PubTatorRelation: combine parameters into a single "text" parameter and use "/search/" endpoint.
        if self._tool_subtype == "PubTatorRelation":
            subject = args.pop("subject_id", None)
            obj = args.pop("object", None)
            rel_type = args.pop("relation_type", None)
            if not subject or not obj:
                raise ValueError(
                    "Missing required parameters 'subject_id' or 'object' for relation search."
                )
            text_value = f"relations:{subject},{obj}"
            if rel_type:
                text_value += f",{rel_type}"
            new_args = {"text": text_value}
            new_args.update(args)
            url = f"{BASE_URL.rstrip('/')}/search/"
            data = None
            headers: Dict[str, str] = {}
            response = requests.request(
                self._method,
                url,
                params=self._query_params(new_args),
                data=data,
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            ctype = response.headers.get("Content-Type", "").lower()
            if "json" in ctype:
                return response.json()
            if "text" in ctype or "xml" in ctype:
                return response.text
            return response.content

        # Special handling for PubTatorAnnotate: override endpoint paths
        if self._tool_subtype == "PubTatorAnnotate":
            if self._method == "POST":
                url = f"{BASE_URL.rstrip('/')}/annotations/annotate"
            else:
                url = f"{BASE_URL.rstrip('/')}/annotations/retrieve"
        else:
            url = self._compose_url(args)

        # ---------- body handling for POST calls ----------
        data: Optional[bytes] = None
        headers: Dict[str, str] = {}
        if self._method == "POST":
            if self._body_param:
                if self._body_param not in args:
                    raise ValueError(
                        f"Missing required body parameter '{self._body_param}'."
                    )
                data = str(args.pop(self._body_param)).encode("utf-8")
                headers["Content-Type"] = "text/plain; charset=utf-8"
            else:
                data = json.dumps(args).encode()
                args.clear()
                headers["Content-Type"] = "application/json"

        # ---------- perform request ----------
        response = requests.request(
            self._method,
            url,
            params=self._query_params(args) if self._method != "POST" else {},
            data=data,
            headers=headers,
            timeout=30,
        )
        if not response.ok:
            return {
                "status": "error",
                "error": f"Request failed with status code {response.status_code}: {response.text}",
            }

        # ---------- auto-detect & return ----------
        ctype = response.headers.get("Content-Type", "").lower()
        if "json" in ctype:
            result = response.json()
            # Extra filtering for PubTatorSearch: filter low-score items and facets.
            if self._tool_subtype == "PubTatorSearch" and isinstance(result, dict):
                result = self._filter_search_results(result)
                # Apply client-side limit: PubTator3 API ignores page_size
                # and always returns 10 results, so truncate here.
                if (
                    _limit is not None
                    and "results" in result
                    and isinstance(result["results"], list)
                ):
                    result["results"] = result["results"][:_limit]
            if isinstance(result, dict) and "status" not in result:
                return {"status": "success", **result}
            return result
        if "text" in ctype or "xml" in ctype:
            return response.text
        return response.content

    # ------------------------------------------------------------------ helpers -----------------
    def _compose_url(self, args: Dict[str, Any]) -> str:
        """Substitute template vars & build full URL."""
        path = self._path
        for placeholder in re.findall(r"{(.*?)}", path):
            if placeholder not in args:
                raise ValueError(f"Missing URL placeholder argument '{placeholder}'.")
            path = path.replace(f"{{{placeholder}}}", str(args.pop(placeholder)))

        if self._id_in_path_key and self._id_in_path_key in args:
            ids_val = args.pop(self._id_in_path_key)
            if isinstance(ids_val, (list, tuple)):
                ids_val = ",".join(map(str, ids_val))
            path = f"{path}/{ids_val}"

        return f"{BASE_URL.rstrip('/')}/{path.lstrip('/')}"

    def _query_params(self, args: Dict[str, Any]) -> Dict[str, str]:
        """Translate caller arg names → API param names, drop Nones, serialise lists."""
        q: Dict[str, str] = {}
        for user_key, val in args.items():
            if val is None:
                continue
            api_key = self._param_map.get(user_key, user_key)
            if isinstance(val, (list, tuple)):
                val = ",".join(map(str, val))
            q[api_key] = str(val)
        return q

    def _filter_search_results(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Filter PubTatorSearch results by score threshold and remove facet items that only have 'name', 'type', and 'value'."""
        # Filter result items based on score threshold.
        # Note: common single-word queries like "cancer" score ~222, so use a
        # conservative threshold to avoid silently dropping all results.
        threshold = 100
        if "results" in result and isinstance(result["results"], list):
            filtered_results = []
            for item in result["results"]:
                score = item.get("score")
                # If there's a numeric score and it's below threshold, skip the item.
                if isinstance(score, (int, float)) and score < threshold:
                    continue
                filtered_results.append(item)
            result["results"] = filtered_results

        # Also filter facets as before.
        if "facets" in result and isinstance(result["facets"], dict):
            del result["facets"]
        return result
