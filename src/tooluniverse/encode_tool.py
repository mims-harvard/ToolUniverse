import json
import requests
from typing import Any, Dict, Optional
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from tooluniverse.tool_registry import register_tool
from tooluniverse.base_rest_tool import BaseRESTTool
from tooluniverse.exceptions import (
    ToolError,
    ToolAuthError,
    ToolRateLimitError,
    ToolUnavailableError,
    ToolValidationError,
    ToolConfigError,
    ToolDependencyError,
    ToolServerError,
)


def _http_get(
    url: str,
    headers: Dict[str, str] | None = None,
    timeout: int = 30,
) -> Dict[str, Any]:
    req = Request(url, headers=headers or {})
    try:
        with urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            try:
                return json.loads(data.decode("utf-8", errors="ignore"))
            except Exception:
                return {"raw": data.decode("utf-8", errors="ignore")}
    except HTTPError as e:
        # ENCODE API may return 404 even with valid JSON data
        # Read the response body from the error
        try:
            data = e.read()
            parsed = json.loads(data.decode("utf-8", errors="ignore"))
            # If we got valid JSON, return it even though status was 404
            return parsed
        except Exception:
            # If we can't parse, re-raise the original error
            raise


def _handle_encode_error(exception: Exception) -> ToolError:
    """Shared error handler for all ENCODE tools - eliminates code duplication."""
    error_str = str(exception).lower()
    if any(
        kw in error_str
        for kw in ["auth", "unauthorized", "401", "403", "api key", "token"]
    ):
        return ToolAuthError(f"Authentication failed: {exception}")
    elif any(
        kw in error_str for kw in ["rate limit", "429", "quota", "limit exceeded"]
    ):
        return ToolRateLimitError(f"Rate limit exceeded: {exception}")
    elif any(
        kw in error_str
        for kw in [
            "unavailable",
            "timeout",
            "connection",
            "network",
            "not found",
            "404",
        ]
    ):
        return ToolUnavailableError(f"Tool unavailable: {exception}")
    elif any(
        kw in error_str for kw in ["validation", "invalid", "schema", "parameter"]
    ):
        return ToolValidationError(f"Validation error: {exception}")
    elif any(kw in error_str for kw in ["config", "configuration", "setup"]):
        return ToolConfigError(f"Configuration error: {exception}")
    elif any(kw in error_str for kw in ["import", "module", "dependency", "package"]):
        return ToolDependencyError(f"Dependency error: {exception}")
    else:
        return ToolServerError(f"Unexpected error: {exception}")


@register_tool(
    "ENCODESearchTool",
    config={
        "name": "ENCODE_search_experiments",
        "type": "ENCODESearchTool",
        "description": "Search ENCODE experiments",
        "parameter": {
            "type": "object",
            "properties": {
                "assay_title": {"type": "string"},
                "target": {"type": "string"},
                "organism": {"type": "string"},
                "status": {"type": "string", "default": "released"},
                "limit": {"type": "integer", "default": 10},
            },
        },
        "settings": {"base_url": "https://www.encodeproject.org", "timeout": 30},
    },
)
class ENCODESearchTool:
    """
    Generic search tool for ENCODE database.

    Searches experiments, files, or biosamples depending on search_type in config.
    Consolidates ENCODESearchTool, ENCODEFilesTool, and ENCODESearchBiosamplesTool.
    """

    def __init__(self, tool_config=None):
        self.tool_config = tool_config or {}

    def handle_error(self, exception: Exception) -> ToolError:
        """Classify exceptions into structured ToolError."""
        return _handle_encode_error(exception)

    def run(self, arguments: Dict[str, Any]):
        # Read from fields.endpoint or settings.base_url
        fields = self.tool_config.get("fields", {})
        settings = self.tool_config.get("settings", {})
        endpoint = fields.get(
            "endpoint",
            settings.get("base_url", "https://www.encodeproject.org/search/"),
        )
        # Extract base URL if endpoint includes /search/
        if endpoint.endswith("/search/"):
            base = endpoint[:-7]  # Remove "/search/"
        else:
            base = endpoint.rstrip("/")
        timeout = int(settings.get("timeout", 30))

        # Get search_type from config fields (default: Experiment)
        # This allows one tool class to handle Experiment, File, and Biosample searches
        search_type = fields.get("search_type", "Experiment")

        query: Dict[str, Any] = {"type": search_type, "format": "json"}

        # Map user-friendly param names to ENCODE API field names
        # ENCODE API uses dot-notation for nested fields
        _param_map = {
            "organism": "replicates.library.biosample.donor.organism.scientific_name",
            "biosample_type": "biosample_ontology.classification",
            # ENCODE API requires biosample_ontology.term_name, not biosample_term_name
            "biosample_term": "biosample_ontology.term_name",
            "biosample": "biosample_ontology.term_name",
            "biosample_term_name": "biosample_ontology.term_name",
            # ENCODE API requires target.label, not bare target
            "target": "target.label",
        }

        # Add all provided arguments to query (remapping as needed)
        for key, value in arguments.items():
            if value is not None:
                mapped_key = _param_map.get(key, key)
                query[mapped_key] = value

        url = f"{base}/search/?{urlencode(query, doseq=True)}"
        try:
            data = _http_get(
                url, headers={"Accept": "application/json"}, timeout=timeout
            )
            return {
                "status": "success",
                "source": "ENCODE",
                "endpoint": "search",
                "query": query,
                "data": data,
                "success": True,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "source": "ENCODE",
                "endpoint": "search",
                "success": False,
            }


# Alias for backward compatibility - all search tools now use ENCODESearchTool
ENCODEFilesTool = ENCODESearchTool
ENCODESearchBiosamplesTool = ENCODESearchTool

# Register the aliases
register_tool("ENCODEFilesTool")(ENCODESearchTool)
register_tool("ENCODESearchBiosamplesTool")(ENCODESearchTool)


@register_tool("ENCODERESTTool")
class ENCODERESTTool(BaseRESTTool):
    """Generic REST tool for ENCODE detail endpoints."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        ENCODE uses custom _http_get helper, so we override the full run method.
        """
        url = None
        try:
            url = self._build_url(arguments)
            # Add format=json parameter for ENCODE
            url_with_format = f"{url}?format=json&frame=object"

            data = _http_get(
                url_with_format,
                headers={"Accept": "application/json"},
                timeout=self.timeout,
            )

            return {
                "status": "success",
                "data": data,
                "url": url,
            }

        except Exception as e:
            return {
                "status": "error",
                "error": f"ENCODE API error: {str(e)}",
                "url": url,
            }
