from typing import Dict, Any, List, Optional
import requests
from .base_tool import BaseTool
from .base_rest_tool import BaseRESTTool
from .tool_registry import register_tool


@register_tool("BioModelsRESTTool")
class BioModelsRESTTool(BaseRESTTool):
    """Generic REST tool for BioModels API endpoints."""

    def _get_param_mapping(self) -> Dict[str, str]:
        """Map BioModels-specific parameter names."""
        if "parameterSearch" in self.tool_config.get("fields", {}).get("endpoint", ""):
            return {
                "limit": "size",
                "offset": "start",
            }
        return {
            "limit": "numResults",  # limit -> numResults
            "offset": "offset",
            # query and filename use their original names
        }

    def _build_params(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Build params while respecting BioModels' minimum upstream page size of 10."""
        params = super()._build_params(args)
        if self.tool_config.get("fields", {}).get("pagination") == "biomodels_offset":
            size_key = "size" if "parameterSearch" in self.tool_config["fields"]["endpoint"] else "numResults"
            if isinstance(params.get(size_key), int) and params[size_key] < 10:
                params[size_key] = 10
        return params

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Validate recoverable offset pagination before invoking BaseRESTTool."""
        if self.tool_config.get("fields", {}).get("pagination") == "biomodels_offset":
            props = self.tool_config.get("parameter", {}).get("properties", {})
            limit = arguments.get("limit", props.get("limit", {}).get("default", 10))
            offset = arguments.get("offset", props.get("offset", {}).get("default", 0))
            if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
                return {"status": "error", "error": "limit must be an integer from 1 to 100"}
            if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
                return {"status": "error", "error": "offset must be a non-negative integer"}
            arguments = dict(arguments, limit=limit, offset=offset)
        return super().run(arguments)

    def _handle_special_endpoint(
        self, url: str, response: requests.Response, arguments: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Handle download endpoints specially."""
        if self.tool_config.get("fields", {}).get("pagination") == "biomodels_offset":
            try:
                data = response.json()
            except ValueError:
                return None
            parameter_search = "parameterSearch" in url
            records_key = "entries" if parameter_search else "models"
            total_key = "recordsFiltered" if parameter_search else "matches"
            records = data.get(records_key, []) if isinstance(data, dict) else []
            if not isinstance(records, list):
                records = []
            limit = arguments["limit"]
            offset = arguments["offset"]
            page = records[:limit]
            total = data.get(total_key) if isinstance(data, dict) else None
            total_is_exact = isinstance(total, int) and not isinstance(total, bool)
            next_offset = offset + len(page)
            stalled = bool(total_is_exact and not page and offset < total)
            has_more = bool(
                total_is_exact and page and next_offset < total
            )
            normalized = dict(data)
            normalized[records_key] = page
            return {
                "status": "success",
                "data": normalized,
                "count": len(page),
                "url": url,
                "metadata": {
                    "returned": len(page),
                    "total_results": total if total_is_exact else None,
                    "total_results_is_exact": total_is_exact,
                    "offset": offset,
                    "limit": limit,
                    "has_more": has_more,
                    "next_offset": next_offset if has_more else None,
                    "truncated": offset > 0 or has_more,
                    "result_set_complete": bool(
                        total_is_exact and offset == 0 and len(page) == total
                    ),
                    "pagination_stalled": stalled,
                    "pagination_scope": (
                        "biomodels_parameter_size_start"
                        if parameter_search
                        else "biomodels_model_numresults_offset"
                    ),
                    "warning": (
                        "BioModels reported additional matches but returned an empty page at this offset."
                        if stalled
                        else None
                    ),
                },
            }
        if "download" in url:
            content_disposition = response.headers.get("Content-Disposition", "")
            content_type = response.headers.get("Content-Type", "")

            # Wrap in data field for schema validation
            return {
                "status": "success",
                "data": {
                    "download_url": url,
                    "filename": content_disposition,
                    "content_type": content_type,
                },
                "url": url,
            }
        return None

    def _process_response(
        self, response: requests.Response, url: str
    ) -> Dict[str, Any]:
        """Process BioModels API response."""
        try:
            data = response.json()
        except ValueError:
            text = response.text or ""
            content_type = response.headers.get("Content-Type", "")
            retryable = "text/html" in content_type.lower() or text.lstrip().startswith("<")
            return {
                "status": "error",
                "error": "BioModels returned a non-JSON response",
                "url": url,
                "content_type": content_type,
                "response_snippet": text[:200],
                "retryable": retryable,
                "suggestion": (
                    "BioModels may have returned an HTML maintenance or redirect page. "
                    "Check the endpoint URL, request parameters, and service availability."
                ),
            }

        # Build result
        result = {
            "status": "success",
            "data": data,
            "url": url,
        }

        # Add count for lists or search results
        if isinstance(data, list):
            result["count"] = len(data)
        elif isinstance(data, dict) and "matches" in data:
            # matches is an integer count, not a list
            result["count"] = data.get("matches", 0)

        return result
