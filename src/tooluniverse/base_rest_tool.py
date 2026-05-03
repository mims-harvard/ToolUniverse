"""
Base REST tool class with common functionality for API integrations.

This module provides a reusable base class for REST API tools that handles:
- URL building with path parameter substitution
- Query parameter construction
- HTTP requests with retry logic
- Standard error handling and response formatting
"""

import os
import requests
import urllib.parse
from typing import Any, Dict, Optional, Callable
from .base_tool import BaseTool
from .http_utils import request_with_retry


class BaseRESTTool(BaseTool):
    """
    Base class for REST API tools with common HTTP request handling.

    Provides reusable methods for:
    - Building URLs with path parameters (e.g., {id}, {doi})
    - Constructing query parameters
    - Making HTTP requests with retry logic
    - Standard error handling and response formatting

    Subclasses should override:
    - `_get_param_mapping()` - to customize parameter name mappings
    - `_process_response()` - to customize response processing
    - `_handle_special_endpoint()` - for endpoint-specific logic
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.session = requests.Session()
        self.timeout = 30
        self.api_name = tool_config.get(
            "name", self.__class__.__name__.replace("RESTTool", "")
        )

    def _get_param_mapping(self) -> Dict[str, str]:
        """
        Get parameter name mappings from argument names to API parameter names.

        Override this in subclasses to provide custom mappings.
        Example: {"limit": "rows", "query": "q"}
        """
        return {}

    def _build_url(self, args: Dict[str, Any]) -> str:
        """
        Build URL by replacing path parameters like {id}, {doi}, {accession}.

        Args:
            args: Tool arguments dictionary

        Returns:
            Complete URL with path parameters substituted
        """
        url = self.tool_config["fields"]["endpoint"]

        # Apply path_aliases: map alias → canonical name before substitution
        path_aliases = self.tool_config.get("fields", {}).get("path_aliases", {})
        for alias, canonical in path_aliases.items():
            if alias in args and canonical not in args:
                args[canonical] = args[alias]

        # Replace all path parameters from user args
        for key, value in args.items():
            placeholder = f"{{{key}}}"
            if placeholder in url:
                # URL encode to handle special characters (e.g., DOIs with slashes)
                encoded_value = urllib.parse.quote(str(value), safe="")
                url = url.replace(placeholder, encoded_value)

        # Apply schema defaults for any remaining {param} placeholders
        for key, prop in (
            self.tool_config.get("parameter", {}).get("properties", {}).items()
        ):
            placeholder = f"{{{key}}}"
            if placeholder in url and "default" in prop and prop["default"] is not None:
                encoded_value = urllib.parse.quote(str(prop["default"]), safe="")
                url = url.replace(placeholder, encoded_value)

        return url

    def _build_params(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build query parameters from arguments.

        Args:
            args: Tool arguments dictionary

        Returns:
            Query parameters dictionary
        """
        params = {}
        url_template = self.tool_config["fields"]["endpoint"]

        # Add default params from config
        default_params = self.tool_config.get("fields", {}).get("params", {})
        params.update(default_params)

        # Get param mapping for this API
        param_mapping = self._get_param_mapping()

        # Params handled client-side only (not sent to API)
        client_only = (
            {"limit"}
            if self.tool_config.get("fields", {}).get("client_side_limit")
            else set()
        )

        for key, value in args.items():
            if (
                key not in client_only
                and f"{{{key}}}" not in url_template
                and value is not None
            ):
                params[param_mapping.get(key, key)] = value

        # Apply schema defaults for optional params not provided by the caller
        for key, prop in (
            self.tool_config.get("parameter", {}).get("properties", {}).items()
        ):
            if (
                key in client_only
                or key in params
                or key in args
                or f"{{{key}}}" in url_template
            ):
                continue
            if "default" in prop and prop["default"] is not None:
                params[param_mapping.get(key, key)] = prop["default"]

        return params

    def _process_response(
        self, response: requests.Response, url: str
    ) -> Dict[str, Any]:
        """
        Process successful API response.

        Override this in subclasses for API-specific response handling.

        Args:
            response: HTTP response object
            url: Request URL

        Returns:
            Processed response dictionary
        """
        try:
            data = response.json()
        except Exception:
            text = response.text
            # Detect HTML error pages returned instead of JSON/text data
            content_type = response.headers.get("content-type", "")
            if "text/html" in content_type or (
                text.strip().startswith(("<html", "<!DOCTYPE", "<HTML"))
            ):
                return {
                    "status": "error",
                    "error": f"{self.api_name}: server returned an HTML page instead of data. The requested resource may not exist.",
                    "url": url,
                }
            # Non-JSON response (e.g., BibTeX, plain text) - return as string
            data = text

        # Handle extract_path for nested data
        extract_path = self.tool_config.get("fields", {}).get("extract_path")
        if extract_path and isinstance(data, dict):
            data = data.get(extract_path, data)

        # Build result
        result = {
            "status": "success",
            "data": data,
            "url": url,
        }

        # Add count for lists
        if isinstance(data, list):
            result["count"] = len(data)

        return result

    def _handle_special_endpoint(
        self, url: str, response: requests.Response, arguments: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Handle special endpoints that need custom processing.

        Override this for endpoint-specific logic (e.g., download endpoints).
        Return None to use default processing.

        Args:
            url: Request URL
            response: HTTP response object
            arguments: Original arguments

        Returns:
            Custom result dictionary or None for default processing
        """
        return None

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the API request.

        Args:
            arguments: Tool arguments dictionary

        Returns:
            Result dictionary with status, data, url, and optional error info
        """
        url = None
        try:
            url = self._build_url(arguments)
            params = self._build_params(arguments)

            # Get custom headers from config (e.g., Accept: application/json)
            custom_headers = dict(
                self.tool_config.get("fields", {}).get("headers") or {}
            )

            # Inject API key from environment variable if auth_header is configured.
            # Config format: {"env_var": "MY_API_KEY", "header": "x-api-key"}
            auth_header_cfg = self.tool_config.get("fields", {}).get("auth_header")
            if auth_header_cfg:
                env_var = auth_header_cfg.get("env_var", "")
                header_name = auth_header_cfg.get("header", "")
                api_key = os.environ.get(env_var, "")
                if not api_key:
                    register_url = auth_header_cfg.get("register_url", "")
                    register_hint = (
                        f" Register at {register_url} to obtain a key."
                        if register_url
                        else ""
                    )
                    return {
                        "status": "error",
                        "error": (
                            f"{self.api_name} requires an API key. "
                            f"Set the {env_var} environment variable.{register_hint}"
                        ),
                    }
                custom_headers[header_name] = api_key

            response = request_with_retry(
                self.session,
                "GET",
                url,
                params=params,
                headers=custom_headers,
                timeout=self.timeout,
                max_attempts=3,
            )

            # Check for errors (accept any 2xx success status)
            if not (200 <= response.status_code < 300):
                return {
                    "status": "error",
                    "error": f"{self.api_name} API error",
                    "url": url,
                    "status_code": response.status_code,
                    "detail": (response.text or "")[:500],
                }

            # Try special endpoint handling first
            special_result = self._handle_special_endpoint(url, response, arguments)
            if special_result is not None:
                return special_result

            # Use default response processing
            result = self._process_response(response, url)

            # Client-side limit for APIs that return unbounded lists
            if self.tool_config.get("fields", {}).get("client_side_limit"):
                props = self.tool_config.get("parameter", {}).get("properties", {})
                limit = arguments.get("limit", props.get("limit", {}).get("default"))
                data = result.get("data")
                if (
                    limit is not None
                    and isinstance(data, list)
                    and len(data) > int(limit)
                ):
                    result["total_before_limit"] = len(data)
                    result["data"] = data[: int(limit)]
                    result["count"] = int(limit)

            return result

        except Exception as e:
            return {
                "status": "error",
                "error": f"{self.api_name} API error: {str(e)}",
                "url": url,
            }
