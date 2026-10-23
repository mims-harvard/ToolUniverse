"""
Base REST tool class with common functionality for API integrations.

This module provides a reusable base class for REST API tools that handles:
- URL building with path parameter substitution
- Query parameter construction
- HTTP requests with retry logic
- Standard error handling and response formatting
"""

import csv
import io
import requests
import urllib.parse
from datetime import date
from typing import Any, Dict, Optional, Callable
from .base_tool import BaseTool
from .http_utils import (
    cloudflare_challenge,
    redact_url_secrets,
    request_with_retry,
    upstream_reason,
)
from .provider_rate_limit import enforce_provider_rate_limit
from .shared_http_session import create_shared_pool_session


# Kept for callers and tests that import it from here.
_upstream_reason = upstream_reason


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

    #: Sent on every request unless a tool's ``fields.headers`` overrides it.
    #: requests defaults to ``python-requests/<version>``, which some public
    #: APIs refuse outright -- Harvard Dataverse answers 403 to it and 200 to
    #: anything else, for the same URL and parameters. Identifying the client
    #: is also what these APIs ask of automated callers.
    USER_AGENT = (
        "ToolUniverse/{version} (+https://github.com/mims-harvard/ToolUniverse)"
    )

    def __init__(self, tool_config):
        super().__init__(tool_config)
        # Keep cookies/headers/auth isolated per tool instance while sharing only the underlying
        # identity-free TCP/TLS transport pools across instances and tenants.
        self.session = create_shared_pool_session()
        self.session.headers["User-Agent"] = self._user_agent()
        self.timeout = 30
        self.api_name = tool_config.get(
            "name", self.__class__.__name__.replace("RESTTool", "")
        )

    @classmethod
    def _user_agent(cls) -> str:
        """Build the User-Agent, tolerating an uninstalled package."""
        try:
            from importlib.metadata import version

            pkg_version = version("tooluniverse")
        except Exception:
            pkg_version = "dev"
        return cls.USER_AGENT.format(version=pkg_version)

    def _get_param_mapping(self) -> Dict[str, str]:
        """
        Get parameter name mappings from argument names to API parameter names.

        Reads ``fields.param_mapping`` from the tool config so pure config-driven
        BaseRESTTool entries can rename query params without a Python subclass
        (e.g. OData APIs needing {"filter": "$filter", "top": "$top"}).
        Subclasses may still override to provide mappings in code.
        Example: {"limit": "rows", "query": "q"}
        """
        return self.tool_config.get("fields", {}).get("param_mapping", {})

    def _build_url(self, args: Dict[str, Any]) -> str:
        """
        Build URL by replacing path parameters like {id}, {doi}, {accession}.

        Args:
            args: Tool arguments dictionary

        Returns:
            Complete URL with path parameters substituted
        """
        url = self.tool_config["fields"]["endpoint"]
        path_param_safe = self.tool_config.get("fields", {}).get("path_param_safe", {})

        # Apply path_aliases: map alias → canonical name before substitution.
        # Fix-R31B-3: an alias key left in `args` after this point leaked into
        # _build_params as an unrecognized query param -- confirmed live this
        # isn't just harmless noise: PostgREST-backed APIs (e.g. CPIC) try to
        # parse every query key as a filter expression and 400 on it
        # ("failed to parse filter"), breaking the whole request. Always pop
        # the alias key once consulted, whether or not the canonical name was
        # already present.
        path_aliases = self.tool_config.get("fields", {}).get("path_aliases", {})
        for alias, canonical in path_aliases.items():
            if alias in args:
                args.setdefault(canonical, args.pop(alias))

        # Replace all path parameters from user args
        for key, value in args.items():
            placeholder = f"{{{key}}}"
            if placeholder in url:
                # URL encode to handle special characters (e.g., DOIs with slashes)
                encoded_value = urllib.parse.quote(
                    str(value), safe=path_param_safe.get(key, "")
                )
                url = url.replace(placeholder, encoded_value)

        # Apply schema defaults for any remaining {param} placeholders
        for key, prop in (
            self.tool_config.get("parameter", {}).get("properties", {}).items()
        ):
            placeholder = f"{{{key}}}"
            if placeholder in url and "default" in prop and prop["default"] is not None:
                encoded_value = urllib.parse.quote(
                    str(prop["default"]), safe=path_param_safe.get(key, "")
                )
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
        client_only = set()
        if self.tool_config.get("fields", {}).get("client_side_limit"):
            client_only.add("limit")
        if self.tool_config.get("fields", {}).get("pagination") == "client_side_offset":
            client_only.add("offset")
        client_only.update(
            self.tool_config.get("fields", {}).get("client_only_params", [])
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

        # Inject an API token from a request credential (or environment fallback) into a query param
        # when configured. Config: {"env_var": "WAQI_API_KEY", "param": "token"}.
        # If the env var is unset the config default (e.g. a public "demo"
        # token) is left in place, so this is a non-breaking opt-in.
        auth_param_cfg = self.tool_config.get("fields", {}).get("auth_param")
        if auth_param_cfg:
            credential = self.credential(auth_param_cfg.get("env_var", ""))
            if credential:
                params[auth_param_cfg.get("param", "token")] = credential

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
        fields = self.tool_config.get("fields", {})

        # Some endpoints return CSV/TSV downloads rather than JSON. When
        # ``fields.parse_csv`` is set, parse the delimited text into a list of
        # dict records (one per data row, keyed by header) so consuming agents
        # get structured data instead of an opaque string blob.
        if fields.get("parse_csv"):
            text = response.text
            content_type = response.headers.get("content-type", "")
            if "text/html" in content_type or text.strip().startswith(
                ("<html", "<!DOCTYPE", "<HTML")
            ):
                return {
                    "status": "error",
                    "error": f"{self.api_name}: server returned an HTML page instead of CSV data. The requested resource may not exist.",
                    "url": url,
                }
            delimiter = fields.get("csv_delimiter", ",")
            reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
            records = [dict(row) for row in reader]
            return {
                "status": "success",
                "data": records,
                "url": url,
                "count": len(records),
                "columns": list(reader.fieldnames or []),
            }

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

        # UniProt collection endpoints expose true totals and opaque next-page
        # cursors in response headers rather than the JSON body. Configs opt in
        # explicitly so a generic BaseRESTTool does not silently discard them.
        if fields.get("pagination") == "uniprot_cursor":
            from .uniprot_pagination import pagination_metadata

            records = data.get("results", []) if isinstance(data, dict) else data
            returned = len(records) if isinstance(records, list) else 0
            result["metadata"] = pagination_metadata(response, returned)

        # Add count for lists
        if isinstance(data, list):
            result["count"] = len(data)

        return result

    @staticmethod
    def _resolve_path(data: Any, path) -> Any:
        """
        Walk a list of dict keys / list indices into a decoded JSON payload.

        Returns None if any step is missing, so callers can treat "not found"
        and "explicitly null" alike (neither is usable as a total/row list).
        """
        current = data
        for step in path or []:
            if isinstance(step, int) and not isinstance(step, bool):
                if not isinstance(current, (list, tuple)) or not (
                    -len(current) <= step < len(current)
                ):
                    return None
                current = current[step]
            else:
                if not isinstance(current, dict) or step not in current:
                    return None
                current = current[step]
        return current

    def _apply_pagination_disclosure(self, result: Dict[str, Any]) -> None:
        """
        Surface upstream truncation at the top level of the response.

        Opt-in via ``fields.pagination_disclosure``; tools without the key are
        untouched. Many APIs return a server-side page of a larger result set
        and report the real total somewhere inside the payload (World Bank puts
        ``{"page","pages","per_page","total"}`` at ``data[0]``; OData services
        return ``@odata.count``). Left buried there, a partial answer is
        indistinguishable from a complete one -- a country panel can lose a
        whole country and still report ``status: success``.

        Config keys (all paths are lists of dict keys / list indices into
        ``result["data"]``)::

            {
              "total_path": [0, "total"],   # int: rows matching upstream
              "rows_path": [1],             # list: rows actually returned
              "page_path": [0, "page"],     # optional int
              "pages_path": [0, "pages"],   # optional int
              "more_hint": "How to fetch the rest."
            }

        Sets ``count`` to the real row count (not the length of an envelope),
        plus ``total_available`` and an explicit ``truncated`` boolean so
        "complete" and "partial" are never conflated. When truncated, adds a
        top-level ``truncation_note`` naming the true total.
        """
        config = self.tool_config.get("fields", {}).get("pagination_disclosure")
        if not config:
            return

        data = result.get("data")
        total = self._resolve_path(data, config.get("total_path"))
        rows = self._resolve_path(data, config.get("rows_path"))
        if not isinstance(total, int) or isinstance(total, bool):
            return
        if not isinstance(rows, list):
            return

        returned = len(rows)
        result["count"] = returned
        result["total_available"] = total
        result["truncated"] = returned < total
        if returned >= total:
            return

        page = self._resolve_path(data, config.get("page_path"))
        pages = self._resolve_path(data, config.get("pages_path"))
        page_part = ""
        if isinstance(page, int) and isinstance(pages, int):
            page_part = f" This is page {page} of {pages}."
        hint = config.get("more_hint", "")
        result["truncation_note"] = (
            f"Partial result: {returned} of {total} matching records were "
            f"returned; {total - returned} are missing.{page_part} "
            f"{hint}"
        ).strip()

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
            ebi_start_page = None
            anaconda_offset_page = None
            eonet_requested_limit = None
            erddap_total = None
            erddap_count_error = None
            usgs_total = None
            usgs_count_error = None
            if (
                self.tool_config.get("fields", {}).get("pagination")
                == "ebi_start_lookahead"
            ):
                props = self.tool_config.get("parameter", {}).get("properties", {})
                size = arguments.get("size", props.get("size", {}).get("default", 20))
                start = arguments.get("start", props.get("start", {}).get("default", 0))
                if (
                    isinstance(size, bool)
                    or not isinstance(size, int)
                    or not 1 <= size <= 999
                ):
                    return {
                        "status": "error",
                        "error": "size must be an integer between 1 and 999",
                        "parameter": "size",
                    }
                if isinstance(start, bool) or not isinstance(start, int) or start < 0:
                    return {
                        "status": "error",
                        "error": "start must be a non-negative integer",
                        "parameter": "start",
                    }
                # EBI's eQTL Catalogue returns a bare array without a count or
                # navigation links. Reserve one of its 1,000 allowed rows for a
                # lookahead record so has_more is evidence-based rather than a
                # guess from a full page.
                ebi_start_page = (start, size)
                arguments = dict(arguments)
                arguments["start"] = start
                arguments["size"] = size + 1

            if self.tool_config.get("fields", {}).get("pagination") == "openfda_skip":
                props = self.tool_config.get("parameter", {}).get("properties", {})
                limit = arguments.get("limit", props.get("limit", {}).get("default", 1))
                skip = arguments.get("skip", props.get("skip", {}).get("default", 0))
                count_mode = bool(arguments.get("count"))
                maximum_limit = 1000 if count_mode else 100
                if (
                    isinstance(limit, bool)
                    or not isinstance(limit, int)
                    or not 1 <= limit <= maximum_limit
                ):
                    return {
                        "status": "error",
                        "error": (
                            f"limit must be an integer between 1 and {maximum_limit}"
                            + (" in openFDA count mode" if count_mode else "")
                        ),
                        "parameter": "limit",
                    }
                if (
                    isinstance(skip, bool)
                    or not isinstance(skip, int)
                    or not 0 <= skip <= 25000
                ):
                    return {
                        "status": "error",
                        "error": "skip must be an integer between 0 and 25000",
                        "parameter": "skip",
                    }
                if count_mode and skip != 0:
                    return {
                        "status": "error",
                        "error": "openFDA does not allow skip when count is used; refine the search or increase limit (max 1000)",
                        "parameter": "skip",
                    }
                arguments = dict(arguments)
                arguments["limit"] = limit
                if count_mode:
                    arguments.pop("skip", None)
                else:
                    arguments["skip"] = skip

            if (
                self.tool_config.get("fields", {}).get("pagination")
                == "drf_limit_offset"
            ):
                props = self.tool_config.get("parameter", {}).get("properties", {})
                limit = arguments.get(
                    "limit", props.get("limit", {}).get("default", 10)
                )
                offset = arguments.get(
                    "offset", props.get("offset", {}).get("default", 0)
                )
                maximum = props.get("limit", {}).get("maximum", 1000)
                if (
                    isinstance(limit, bool)
                    or not isinstance(limit, int)
                    or not 1 <= limit <= maximum
                ):
                    return {
                        "status": "error",
                        "error": f"limit must be an integer between 1 and {maximum}",
                        "parameter": "limit",
                    }
                if (
                    isinstance(offset, bool)
                    or not isinstance(offset, int)
                    or offset < 0
                ):
                    return {
                        "status": "error",
                        "error": "offset must be a non-negative integer",
                        "parameter": "offset",
                    }
                arguments = dict(arguments)
                arguments["limit"] = limit
                arguments["offset"] = offset

            if self.tool_config.get("fields", {}).get("pagination") == "biorxiv_cursor":
                cursor = arguments.get("cursor", 0)
                if (
                    isinstance(cursor, bool)
                    or not isinstance(cursor, int)
                    or cursor < 0
                ):
                    return {
                        "status": "error",
                        "error": "cursor must be a non-negative integer record offset",
                        "parameter": "cursor",
                    }
                parsed_dates = {}
                for key in ("start_date", "end_date"):
                    value = arguments.get(key)
                    try:
                        parsed_dates[key] = date.fromisoformat(value)
                    except (TypeError, ValueError):
                        return {
                            "status": "error",
                            "error": f"{key} must be a valid date in YYYY-MM-DD format",
                            "parameter": key,
                        }
                if parsed_dates["start_date"] > parsed_dates["end_date"]:
                    return {
                        "status": "error",
                        "error": "start_date must be earlier than or equal to end_date",
                        "parameter": "start_date",
                    }
                arguments = dict(arguments)
                arguments["cursor"] = cursor

            if (
                self.tool_config.get("fields", {}).get("pagination")
                == "marine_regions_offset"
            ):
                offset = arguments.get("offset", 0)
                if (
                    isinstance(offset, bool)
                    or not isinstance(offset, int)
                    or offset < 0
                ):
                    return {
                        "status": "error",
                        "error": "offset must be a non-negative integer",
                        "parameter": "offset",
                    }
                for key, default in (("like", True), ("fuzzy", False)):
                    value = arguments.get(key, default)
                    if not isinstance(value, bool):
                        return {
                            "status": "error",
                            "error": f"{key} must be a boolean",
                            "parameter": key,
                        }
                arguments = dict(arguments)
                arguments["offset"] = offset
                arguments.setdefault("like", True)
                arguments.setdefault("fuzzy", False)

            if self.tool_config.get("fields", {}).get("pagination") == "dblp_offset":
                limit = arguments.get("limit", 10)
                offset = arguments.get("offset", 0)
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
                if (
                    isinstance(offset, bool)
                    or not isinstance(offset, int)
                    or offset < 0
                ):
                    return {
                        "status": "error",
                        "error": "offset must be a non-negative integer",
                        "parameter": "offset",
                    }

            if (
                self.tool_config.get("fields", {}).get("pagination")
                == "nci_drugdict_offset"
            ):
                props = self.tool_config.get("parameter", {}).get("properties", {})
                size = arguments.get("size", props.get("size", {}).get("default", 10))
                offset_key = self.tool_config.get("fields", {}).get(
                    "offset_parameter", "offset"
                )
                offset = arguments.get(
                    offset_key, props.get(offset_key, {}).get("default", 0)
                )
                maximum = props.get("size", {}).get("maximum")
                if (
                    isinstance(size, bool)
                    or not isinstance(size, int)
                    or size < 1
                    or (isinstance(maximum, int) and size > maximum)
                ):
                    return {
                        "status": "error",
                        "error": (
                            f"size must be an integer between 1 and {maximum}"
                            if isinstance(maximum, int)
                            else "size must be a positive integer"
                        ),
                        "parameter": "size",
                    }
                if (
                    isinstance(offset, bool)
                    or not isinstance(offset, int)
                    or offset < 0
                ):
                    return {
                        "status": "error",
                        "error": f"{offset_key} must be a non-negative integer",
                        "parameter": offset_key,
                    }
                arguments = dict(arguments)
                arguments["size"] = size
                arguments[offset_key] = offset

            if self.tool_config.get("fields", {}).get("pagination") == "eva_skip":
                props = self.tool_config.get("parameter", {}).get("properties", {})
                limit = arguments.get(
                    "limit", props.get("limit", {}).get("default", 20)
                )
                offset = arguments.get(
                    "offset", props.get("offset", {}).get("default", 0)
                )
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
                if (
                    isinstance(offset, bool)
                    or not isinstance(offset, int)
                    or offset < 0
                ):
                    return {
                        "status": "error",
                        "error": "offset must be a non-negative integer",
                        "parameter": "offset",
                    }
                if offset % limit:
                    return {
                        "status": "error",
                        "error": (
                            "offset must be a multiple of limit because EVA rounds skip "
                            "down to a page boundary; use metadata.next_offset with the same limit"
                        ),
                        "parameter": "offset",
                    }

            if (
                self.tool_config.get("fields", {}).get("pagination")
                == "intermine_start"
            ):
                props = self.tool_config.get("parameter", {}).get("properties", {})
                size = arguments.get("size", props.get("size", {}).get("default", 10))
                start = arguments.get("start", props.get("start", {}).get("default", 0))
                if size is None:
                    size = 10
                if start is None:
                    start = 0
                if (
                    isinstance(size, bool)
                    or not isinstance(size, int)
                    or not 1 <= size <= 100
                ):
                    return {
                        "status": "error",
                        "error": "size must be an integer between 1 and 100",
                        "parameter": "size",
                    }
                if isinstance(start, bool) or not isinstance(start, int) or start < 0:
                    return {
                        "status": "error",
                        "error": "start must be a non-negative integer",
                        "parameter": "start",
                    }
                arguments = dict(arguments)
                arguments["size"] = size
                arguments["start"] = start

            if (
                self.tool_config.get("fields", {}).get("pagination")
                == "client_side_offset"
            ):
                props = self.tool_config.get("parameter", {}).get("properties", {})
                limit = arguments.get(
                    "limit", props.get("limit", {}).get("default", 100)
                )
                offset = arguments.get(
                    "offset", props.get("offset", {}).get("default", 0)
                )
                if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
                    return {
                        "status": "error",
                        "error": "limit must be a positive integer",
                        "parameter": "limit",
                    }
                if (
                    isinstance(offset, bool)
                    or not isinstance(offset, int)
                    or offset < 0
                ):
                    return {
                        "status": "error",
                        "error": "offset must be a non-negative integer",
                        "parameter": "offset",
                    }
                arguments = dict(arguments)
                arguments["limit"] = limit
                arguments["offset"] = offset

            if (
                self.tool_config.get("fields", {}).get("pagination")
                == "huggingface_cursor"
            ):
                props = self.tool_config.get("parameter", {}).get("properties", {})
                limit = arguments.get(
                    "limit", props.get("limit", {}).get("default", 20)
                )
                cursor = arguments.get("cursor")
                if limit is None:
                    limit = 20
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
                if cursor is not None and (not isinstance(cursor, str) or not cursor):
                    return {
                        "status": "error",
                        "error": "cursor must be a non-empty string when provided",
                        "parameter": "cursor",
                    }
                arguments = dict(arguments)
                arguments["limit"] = limit

            if (
                self.tool_config.get("fields", {}).get("pagination")
                == "semantic_scholar_offset"
            ):
                props = self.tool_config.get("parameter", {}).get("properties", {})
                limit = arguments.get("limit", props.get("limit", {}).get("default", 5))
                offset = arguments.get(
                    "offset", props.get("offset", {}).get("default", 0)
                )
                if offset is None:
                    offset = 0
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
                if (
                    isinstance(offset, bool)
                    or not isinstance(offset, int)
                    or offset < 0
                ):
                    return {
                        "status": "error",
                        "error": "offset must be a non-negative integer",
                        "parameter": "offset",
                    }
                arguments = dict(arguments)
                arguments["limit"] = limit
                arguments["offset"] = offset

            if self.tool_config.get("fields", {}).get("pagination") == "runiverse_skip":
                props = self.tool_config.get("parameter", {}).get("properties", {})
                limit = arguments.get(
                    "limit", props.get("limit", {}).get("default", 10)
                )
                offset = arguments.get(
                    "offset", props.get("offset", {}).get("default", 0)
                )
                if limit is None:
                    limit = 10
                if (
                    isinstance(limit, bool)
                    or not isinstance(limit, int)
                    or not 1 <= limit <= 100
                ):
                    return {
                        "status": "error",
                        "error": "limit must be an integer between 1 and 100",
                        "parameter": "limit",
                    }
                if (
                    isinstance(offset, bool)
                    or not isinstance(offset, int)
                    or offset < 0
                ):
                    return {
                        "status": "error",
                        "error": "offset must be a non-negative integer",
                        "parameter": "offset",
                    }
                arguments = dict(arguments)
                arguments["limit"] = limit
                arguments["offset"] = offset

            if self.tool_config.get("fields", {}).get("pagination") == "tess_page":
                props = self.tool_config.get("parameter", {}).get("properties", {})
                page_size = arguments.get(
                    "page_size", props.get("page_size", {}).get("default", 10)
                )
                page = arguments.get("page", props.get("page", {}).get("default", 1))
                if page_size is None:
                    page_size = 10
                if page is None:
                    page = 1
                if (
                    isinstance(page_size, bool)
                    or not isinstance(page_size, int)
                    or not 1 <= page_size <= 100
                ):
                    return {
                        "status": "error",
                        "error": "page_size must be an integer between 1 and 100",
                        "parameter": "page_size",
                    }
                if isinstance(page, bool) or not isinstance(page, int) or page < 1:
                    return {
                        "status": "error",
                        "error": "page must be an integer greater than or equal to 1",
                        "parameter": "page",
                    }
                arguments = dict(arguments)
                arguments["page_size"] = page_size
                arguments["page"] = page

            if (
                self.tool_config.get("fields", {}).get("pagination")
                == "openml_offset_path"
            ):
                props = self.tool_config.get("parameter", {}).get("properties", {})
                limit = arguments.get(
                    "limit", props.get("limit", {}).get("default", 20)
                )
                offset = arguments.get(
                    "offset", props.get("offset", {}).get("default", 0)
                )
                if (
                    isinstance(limit, bool)
                    or not isinstance(limit, int)
                    or not 1 <= limit <= 10000
                ):
                    return {
                        "status": "error",
                        "error": "limit must be an integer between 1 and 10000",
                        "parameter": "limit",
                    }
                if (
                    isinstance(offset, bool)
                    or not isinstance(offset, int)
                    or offset < 0
                ):
                    return {
                        "status": "error",
                        "error": "offset must be a non-negative integer",
                        "parameter": "offset",
                    }
                arguments = dict(arguments)
                arguments["limit"] = limit
                arguments["offset"] = offset

            if self.tool_config.get("fields", {}).get("pagination") == "cmr_page":
                props = self.tool_config.get("parameter", {}).get("properties", {})
                page_size = arguments.get(
                    "page_size", props.get("page_size", {}).get("default", 10)
                )
                page = arguments.get("page", props.get("page", {}).get("default", 1))
                if page_size is None:
                    page_size = 10
                if (
                    isinstance(page_size, bool)
                    or not isinstance(page_size, int)
                    or not 1 <= page_size <= 2000
                ):
                    return {
                        "status": "error",
                        "error": "page_size must be an integer between 1 and 2000",
                        "parameter": "page_size",
                    }
                if isinstance(page, bool) or not isinstance(page, int) or page < 1:
                    return {
                        "status": "error",
                        "error": "page must be an integer greater than or equal to 1",
                        "parameter": "page",
                    }
                arguments = dict(arguments)
                arguments["page_size"] = page_size
                arguments["page"] = page

            if self.tool_config.get("fields", {}).get("pagination") == "inspire_page":
                props = self.tool_config.get("parameter", {}).get("properties", {})
                size = arguments.get("size", props.get("size", {}).get("default", 10))
                page = arguments.get("page", props.get("page", {}).get("default", 1))
                if size is None:
                    size = 10
                if (
                    isinstance(size, bool)
                    or not isinstance(size, int)
                    or not 1 <= size <= 25
                ):
                    return {
                        "status": "error",
                        "error": "size must be an integer between 1 and 25",
                        "parameter": "size",
                    }
                if isinstance(page, bool) or not isinstance(page, int) or page < 1:
                    return {
                        "status": "error",
                        "error": "page must be an integer greater than or equal to 1",
                        "parameter": "page",
                    }
                arguments = dict(arguments)
                arguments["size"] = size
                arguments["page"] = page

            if (
                self.tool_config.get("fields", {}).get("pagination")
                == "worldbank_indicator_search"
            ):
                props = self.tool_config.get("parameter", {}).get("properties", {})
                query = arguments.get("query")
                per_page = arguments.get(
                    "per_page", props.get("per_page", {}).get("default", 10)
                )
                offset = arguments.get(
                    "offset", props.get("offset", {}).get("default", 0)
                )
                if not isinstance(query, str) or not query.strip():
                    return {
                        "status": "error",
                        "error": "query must be a non-empty string",
                        "parameter": "query",
                    }
                if per_page is None:
                    per_page = 10
                if (
                    isinstance(per_page, bool)
                    or not isinstance(per_page, int)
                    or not 1 <= per_page <= 1000
                ):
                    return {
                        "status": "error",
                        "error": "per_page must be an integer between 1 and 1000",
                        "parameter": "per_page",
                    }
                if (
                    isinstance(offset, bool)
                    or not isinstance(offset, int)
                    or offset < 0
                ):
                    return {
                        "status": "error",
                        "error": "offset must be a non-negative integer",
                        "parameter": "offset",
                    }
                arguments = dict(arguments)
                arguments["query"] = query.strip()
                arguments["per_page"] = per_page
                arguments["offset"] = offset

            if self.tool_config.get("fields", {}).get("pagination") == "artic_page":
                props = self.tool_config.get("parameter", {}).get("properties", {})
                limit = arguments.get(
                    "limit", props.get("limit", {}).get("default", 10)
                )
                page = arguments.get("page", props.get("page", {}).get("default", 1))
                if limit is None:
                    limit = 10
                if (
                    isinstance(limit, bool)
                    or not isinstance(limit, int)
                    or not 1 <= limit <= 100
                ):
                    return {
                        "status": "error",
                        "error": "limit must be an integer between 1 and 100",
                        "parameter": "limit",
                    }
                if isinstance(page, bool) or not isinstance(page, int) or page < 1:
                    return {
                        "status": "error",
                        "error": "page must be an integer greater than or equal to 1",
                        "parameter": "page",
                    }
                arguments = dict(arguments)
                arguments["limit"] = limit
                arguments["page"] = page

            if (
                self.tool_config.get("fields", {}).get("pagination")
                == "github_search_page"
            ):
                props = self.tool_config.get("parameter", {}).get("properties", {})
                per_page = arguments.get(
                    "per_page", props.get("per_page", {}).get("default", 30)
                )
                page = arguments.get("page", props.get("page", {}).get("default", 1))
                if per_page is None:
                    per_page = 30
                if (
                    isinstance(per_page, bool)
                    or not isinstance(per_page, int)
                    or not 1 <= per_page <= 100
                ):
                    return {
                        "status": "error",
                        "error": "per_page must be an integer between 1 and 100",
                        "parameter": "per_page",
                    }
                if isinstance(page, bool) or not isinstance(page, int) or page < 1:
                    return {
                        "status": "error",
                        "error": "page must be an integer greater than or equal to 1",
                        "parameter": "page",
                    }
                if (page - 1) * per_page >= 1000:
                    return {
                        "status": "error",
                        "error": (
                            "page and per_page exceed GitHub Search's first-1000-results retrieval window"
                        ),
                        "parameter": "page",
                    }
                arguments = dict(arguments)
                arguments["per_page"] = per_page
                arguments["page"] = page

            if (
                self.tool_config.get("fields", {}).get("pagination")
                == "usgs_offset_count"
            ):
                props = self.tool_config.get("parameter", {}).get("properties", {})
                limit = arguments.get(
                    "limit", props.get("limit", {}).get("default", 20000)
                )
                offset = arguments.get(
                    "offset", props.get("offset", {}).get("default", 1)
                )
                if limit is None:
                    limit = 20000
                if (
                    isinstance(limit, bool)
                    or not isinstance(limit, int)
                    or not 1 <= limit <= 20000
                ):
                    return {
                        "status": "error",
                        "error": "limit must be an integer between 1 and 20000",
                        "parameter": "limit",
                    }
                if (
                    isinstance(offset, bool)
                    or not isinstance(offset, int)
                    or offset < 1
                ):
                    return {
                        "status": "error",
                        "error": "offset must be a one-based positive integer",
                        "parameter": "offset",
                    }
                arguments = dict(arguments)
                arguments["limit"] = limit
                arguments["offset"] = offset
                arguments.setdefault("orderby", "time")

            if (
                self.tool_config.get("fields", {}).get("pagination")
                == "nws_client_offset"
            ):
                props = self.tool_config.get("parameter", {}).get("properties", {})
                limit = arguments.get(
                    "limit", props.get("limit", {}).get("default", 50)
                )
                offset = arguments.get(
                    "offset", props.get("offset", {}).get("default", 0)
                )
                if limit is None:
                    limit = 50
                if (
                    isinstance(limit, bool)
                    or not isinstance(limit, int)
                    or not 1 <= limit <= 500
                ):
                    return {
                        "status": "error",
                        "error": "limit must be an integer between 1 and 500",
                        "parameter": "limit",
                    }
                if (
                    isinstance(offset, bool)
                    or not isinstance(offset, int)
                    or offset < 0
                ):
                    return {
                        "status": "error",
                        "error": "offset must be a non-negative integer",
                        "parameter": "offset",
                    }
                arguments = dict(arguments)
                arguments["limit"] = limit
                arguments["offset"] = offset

            if self.tool_config.get("fields", {}).get("pagination") == "jpl_cad_offset":
                props = self.tool_config.get("parameter", {}).get("properties", {})
                limit = arguments.get(
                    "limit", props.get("limit", {}).get("default", 50)
                )
                offset = arguments.get(
                    "offset", props.get("offset", {}).get("default", 0)
                )
                if limit is None:
                    limit = 50
                if (
                    isinstance(limit, bool)
                    or not isinstance(limit, int)
                    or not 1 <= limit <= 10000
                ):
                    return {
                        "status": "error",
                        "error": "limit must be an integer between 1 and 10000",
                        "parameter": "limit",
                    }
                if (
                    isinstance(offset, bool)
                    or not isinstance(offset, int)
                    or offset < 0
                ):
                    return {
                        "status": "error",
                        "error": "offset must be a non-negative integer",
                        "parameter": "offset",
                    }
                arguments = dict(arguments)
                arguments["limit"] = limit
                arguments["offset"] = offset
                arguments.setdefault("sort", "date")

            if (
                self.tool_config.get("fields", {}).get("pagination")
                == "wikidata_continue"
            ):
                props = self.tool_config.get("parameter", {}).get("properties", {})
                limit = arguments.get("limit", props.get("limit", {}).get("default", 7))
                cursor = arguments.get(
                    "continue", props.get("continue", {}).get("default", 0)
                )
                if limit is None:
                    limit = 7
                if (
                    isinstance(limit, bool)
                    or not isinstance(limit, int)
                    or not 1 <= limit <= 50
                ):
                    return {
                        "status": "error",
                        "error": "limit must be an integer between 1 and 50",
                        "parameter": "limit",
                    }
                if (
                    isinstance(cursor, bool)
                    or not isinstance(cursor, int)
                    or cursor < 0
                ):
                    return {
                        "status": "error",
                        "error": "continue must be a non-negative integer",
                        "parameter": "continue",
                    }
                arguments = dict(arguments)
                arguments["limit"] = limit
                arguments["continue"] = cursor

            if self.tool_config.get("fields", {}).get("pagination") == "ror_page":
                props = self.tool_config.get("parameter", {}).get("properties", {})
                page = arguments.get("page", props.get("page", {}).get("default", 1))
                if isinstance(page, bool) or not isinstance(page, int) or page < 1:
                    return {
                        "status": "error",
                        "error": "page must be an integer greater than or equal to 1",
                        "parameter": "page",
                    }
                arguments = dict(arguments)
                arguments["page"] = page

            if self.tool_config.get("fields", {}).get("pagination") == "nci_r4r_from":
                props = self.tool_config.get("parameter", {}).get("properties", {})
                size = arguments.get("size", props.get("size", {}).get("default", 20))
                start = arguments.get("from", props.get("from", {}).get("default", 0))
                if (
                    isinstance(size, bool)
                    or not isinstance(size, int)
                    or not 1 <= size <= 50
                ):
                    return {
                        "status": "error",
                        "error": "size must be an integer between 1 and 50",
                        "parameter": "size",
                    }
                if isinstance(start, bool) or not isinstance(start, int) or start < 0:
                    return {
                        "status": "error",
                        "error": "from must be a non-negative integer",
                        "parameter": "from",
                    }
                arguments = dict(arguments)
                arguments["size"] = size
                arguments["from"] = start

            if self.tool_config.get("fields", {}).get("pagination") == "ncbi_esearch":
                props = self.tool_config.get("parameter", {}).get("properties", {})
                retmax = arguments.get(
                    "retmax", props.get("retmax", {}).get("default", 10)
                )
                retstart = arguments.get(
                    "retstart", props.get("retstart", {}).get("default", 0)
                )
                if (
                    isinstance(retmax, bool)
                    or not isinstance(retmax, int)
                    or not 1 <= retmax <= 100
                ):
                    return {
                        "status": "error",
                        "error": "retmax must be an integer between 1 and 100",
                        "parameter": "retmax",
                    }
                if (
                    isinstance(retstart, bool)
                    or not isinstance(retstart, int)
                    or retstart < 0
                ):
                    return {
                        "status": "error",
                        "error": "retstart must be a non-negative integer",
                        "parameter": "retstart",
                    }
                arguments = dict(arguments)
                arguments["retmax"] = retmax
                arguments["retstart"] = retstart

            if (
                self.tool_config.get("fields", {}).get("pagination")
                == "anaconda_offset_lookahead"
            ):
                props = self.tool_config.get("parameter", {}).get("properties", {})
                limit = arguments.get(
                    "limit", props.get("limit", {}).get("default", 20)
                )
                offset = arguments.get(
                    "offset", props.get("offset", {}).get("default", 0)
                )
                if (
                    isinstance(limit, bool)
                    or not isinstance(limit, int)
                    or not 1 <= limit <= 100
                ):
                    return {
                        "status": "error",
                        "error": "limit must be an integer between 1 and 100",
                        "parameter": "limit",
                    }
                if (
                    isinstance(offset, bool)
                    or not isinstance(offset, int)
                    or offset < 0
                ):
                    return {
                        "status": "error",
                        "error": "offset must be a non-negative integer",
                        "parameter": "offset",
                    }
                anaconda_offset_page = (offset, limit)
                arguments = dict(arguments)
                arguments["limit"] = limit + 1
                arguments["offset"] = offset

            if (
                self.tool_config.get("fields", {}).get("pagination")
                == "eva_studies_client_sort"
            ):
                props = self.tool_config.get("parameter", {}).get("properties", {})
                limit = arguments.get(
                    "limit", props.get("limit", {}).get("default", 20)
                )
                offset = arguments.get(
                    "offset", props.get("offset", {}).get("default", 0)
                )
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
                if (
                    isinstance(offset, bool)
                    or not isinstance(offset, int)
                    or offset < 0
                ):
                    return {
                        "status": "error",
                        "error": "offset must be a non-negative integer",
                        "parameter": "offset",
                    }
                arguments = dict(arguments)
                arguments["limit"] = limit
                arguments["offset"] = offset

            if self.tool_config.get("fields", {}).get("pagination") == "panelapp_page":
                props = self.tool_config.get("parameter", {}).get("properties", {})
                page = arguments.get("page", props.get("page", {}).get("default", 1))
                if isinstance(page, bool) or not isinstance(page, int) or page < 1:
                    return {
                        "status": "error",
                        "error": "page must be an integer greater than or equal to 1",
                        "parameter": "page",
                    }
                arguments = dict(arguments)
                arguments["page"] = page

            if self.tool_config.get("fields", {}).get("pagination") == "litvar_top_n":
                props = self.tool_config.get("parameter", {}).get("properties", {})
                limit = arguments.get(
                    "limit", props.get("limit", {}).get("default", 10)
                )
                if (
                    isinstance(limit, bool)
                    or not isinstance(limit, int)
                    or not 1 <= limit <= 100
                ):
                    return {
                        "status": "error",
                        "error": "limit must be an integer between 1 and 100",
                        "parameter": "limit",
                    }
                arguments = dict(arguments)
                arguments["limit"] = limit

            if (
                self.tool_config.get("fields", {}).get("pagination")
                == "litvar_publications_local"
            ):
                props = self.tool_config.get("parameter", {}).get("properties", {})
                maximum = props.get("max", {}).get("maximum", 1000)
                page_size = arguments.get(
                    "max", props.get("max", {}).get("default", 50)
                )
                offset = arguments.get(
                    "offset", props.get("offset", {}).get("default", 0)
                )
                if (
                    isinstance(page_size, bool)
                    or not isinstance(page_size, int)
                    or not 1 <= page_size <= maximum
                ):
                    return {
                        "status": "error",
                        "error": f"max must be an integer between 1 and {maximum}",
                        "parameter": "max",
                    }
                if (
                    isinstance(offset, bool)
                    or not isinstance(offset, int)
                    or offset < 0
                ):
                    return {
                        "status": "error",
                        "error": "offset must be a non-negative integer",
                        "parameter": "offset",
                    }
                arguments = dict(arguments)
                arguments["max"] = page_size
                arguments["offset"] = offset

            if (
                self.tool_config.get("fields", {}).get("pagination")
                == "idr_meta_offset"
            ):
                props = self.tool_config.get("parameter", {}).get("properties", {})
                limit = arguments.get(
                    "limit", props.get("limit", {}).get("default", 25)
                )
                offset = arguments.get(
                    "offset", props.get("offset", {}).get("default", 0)
                )
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
                if (
                    isinstance(offset, bool)
                    or not isinstance(offset, int)
                    or offset < 0
                ):
                    return {
                        "status": "error",
                        "error": "offset must be a non-negative integer",
                        "parameter": "offset",
                    }
                arguments = dict(arguments)
                arguments["limit"] = limit
                arguments["offset"] = offset

            if self.tool_config.get("fields", {}).get("pagination") == "spring_page":
                props = self.tool_config.get("parameter", {}).get("properties", {})
                page = arguments.get("page", props.get("page", {}).get("default", 0))
                size = arguments.get("size", props.get("size", {}).get("default", 20))
                if isinstance(page, bool) or not isinstance(page, int) or page < 0:
                    return {
                        "status": "error",
                        "error": "page must be a non-negative integer",
                        "parameter": "page",
                    }
                if (
                    isinstance(size, bool)
                    or not isinstance(size, int)
                    or not 1 <= size <= 1000
                ):
                    return {
                        "status": "error",
                        "error": "size must be an integer between 1 and 1000",
                        "parameter": "size",
                    }
                arguments = dict(arguments)
                arguments["page"] = page
                arguments["size"] = size

            if self.tool_config.get("fields", {}).get("pagination") == "drf_page":
                props = self.tool_config.get("parameter", {}).get("properties", {})
                page = arguments.get("page", props.get("page", {}).get("default", 1))
                if isinstance(page, bool) or not isinstance(page, int) or page < 1:
                    return {
                        "status": "error",
                        "error": "page must be an integer greater than or equal to 1",
                        "parameter": "page",
                    }
                arguments = dict(arguments)
                arguments["page"] = page

            if self.tool_config.get("fields", {}).get("pagination") == "dryad_hal_page":
                props = self.tool_config.get("parameter", {}).get("properties", {})
                page = arguments.get("page", props.get("page", {}).get("default", 1))
                per_page = arguments.get(
                    "per_page", props.get("per_page", {}).get("default", 10)
                )
                if isinstance(page, bool) or not isinstance(page, int) or page < 1:
                    return {
                        "status": "error",
                        "error": "page must be an integer greater than or equal to 1",
                        "parameter": "page",
                    }
                if (
                    isinstance(per_page, bool)
                    or not isinstance(per_page, int)
                    or not 1 <= per_page <= 100
                ):
                    return {
                        "status": "error",
                        "error": "per_page must be an integer between 1 and 100",
                        "parameter": "per_page",
                    }
                arguments = dict(arguments)
                arguments["page"] = page
                arguments["per_page"] = per_page

            if self.tool_config.get("fields", {}).get("pagination") == "col_offset":
                props = self.tool_config.get("parameter", {}).get("properties", {})
                limit = arguments.get(
                    "limit", props.get("limit", {}).get("default", 10)
                )
                offset = arguments.get(
                    "offset", props.get("offset", {}).get("default", 0)
                )
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
                if (
                    isinstance(offset, bool)
                    or not isinstance(offset, int)
                    or not 0 <= offset <= 100000
                ):
                    return {
                        "status": "error",
                        "error": "offset must be an integer between 0 and 100000",
                        "parameter": "offset",
                    }
                arguments = dict(arguments)
                arguments["limit"] = limit
                arguments["offset"] = offset

            if self.tool_config.get("fields", {}).get("pagination") == "biotools_page":
                props = self.tool_config.get("parameter", {}).get("properties", {})
                page = arguments.get("page", props.get("page", {}).get("default", 1))
                size = arguments.get("size", props.get("size", {}).get("default", 10))
                response_format = arguments.get("format", "json")
                if isinstance(page, bool) or not isinstance(page, int) or page < 1:
                    return {
                        "status": "error",
                        "error": "page must be an integer greater than or equal to 1",
                        "parameter": "page",
                    }
                if (
                    isinstance(size, bool)
                    or not isinstance(size, int)
                    or not 1 <= size <= 100
                ):
                    return {
                        "status": "error",
                        "error": "size must be an integer between 1 and 100",
                        "parameter": "size",
                    }
                if response_format != "json":
                    return {
                        "status": "error",
                        "error": "format must be 'json'",
                        "parameter": "format",
                    }
                arguments = dict(arguments)
                arguments["page"] = page
                arguments["size"] = size
                arguments["format"] = response_format

            if self.tool_config.get("fields", {}).get("pagination") == "eonet_top_n":
                props = self.tool_config.get("parameter", {}).get("properties", {})
                limit = arguments.get(
                    "limit", props.get("limit", {}).get("default", 10)
                )
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
                status = arguments.get("status")
                if isinstance(status, str):
                    status = status.lower()
                if status is not None and status not in {"open", "closed", "all"}:
                    return {
                        "status": "error",
                        "error": "status must be one of: open, closed, all",
                        "parameter": "status",
                    }
                valid_categories = set(props.get("category", {}).get("enum", []))
                category = arguments.get("category")
                if category is not None and category not in valid_categories:
                    return {
                        "status": "error",
                        "error": (
                            "category must be one of: "
                            + ", ".join(sorted(valid_categories))
                        ),
                        "parameter": "category",
                    }
                eonet_requested_limit = limit
                arguments = dict(arguments)
                arguments["limit"] = limit + 1
                if status is not None:
                    arguments["status"] = status

            if self.tool_config.get("fields", {}).get("pagination") == "dataone_solr":
                props = self.tool_config.get("parameter", {}).get("properties", {})
                rows = arguments.get("rows", props.get("rows", {}).get("default", 10))
                start = arguments.get("start", props.get("start", {}).get("default", 0))
                if (
                    isinstance(rows, bool)
                    or not isinstance(rows, int)
                    or not 1 <= rows <= 1000
                ):
                    return {
                        "status": "error",
                        "error": "rows must be an integer between 1 and 1000",
                        "parameter": "rows",
                    }
                if isinstance(start, bool) or not isinstance(start, int) or start < 0:
                    return {
                        "status": "error",
                        "error": "start must be a non-negative integer",
                        "parameter": "start",
                    }
                arguments = dict(arguments)
                arguments["rows"] = rows
                arguments["start"] = start

            if self.tool_config.get("fields", {}).get("pagination") == "ceda_offset":
                props = self.tool_config.get("parameter", {}).get("properties", {})
                limit = arguments.get(
                    "limit", props.get("limit", {}).get("default", 10)
                )
                offset = arguments.get(
                    "offset", props.get("offset", {}).get("default", 0)
                )
                if (
                    isinstance(limit, bool)
                    or not isinstance(limit, int)
                    or not 1 <= limit <= 100
                ):
                    return {
                        "status": "error",
                        "error": "limit must be an integer between 1 and 100",
                        "parameter": "limit",
                    }
                if (
                    isinstance(offset, bool)
                    or not isinstance(offset, int)
                    or offset < 0
                ):
                    return {
                        "status": "error",
                        "error": "offset must be a non-negative integer",
                        "parameter": "offset",
                    }
                search_field = arguments.get("search_field", "title")
                if search_field not in {"title", "abstract", "keywords"}:
                    return {
                        "status": "error",
                        "error": "search_field must be one of: title, abstract, keywords",
                        "parameter": "search_field",
                    }
                query = arguments.get("q")
                arguments = {
                    key: value
                    for key, value in arguments.items()
                    if key not in {"q", "search_field"}
                }
                arguments["limit"] = limit
                arguments["offset"] = offset
                if isinstance(query, str) and query:
                    arguments[f"{search_field}__icontains"] = query

            if self.tool_config.get("fields", {}).get("pagination") == "erddap_page":
                props = self.tool_config.get("parameter", {}).get("properties", {})
                page = arguments.get("page", props.get("page", {}).get("default", 1))
                items = arguments.get(
                    "itemsPerPage",
                    props.get("itemsPerPage", {}).get("default", 10),
                )
                if isinstance(page, bool) or not isinstance(page, int) or page < 1:
                    return {
                        "status": "error",
                        "error": "page must be an integer greater than or equal to 1",
                        "parameter": "page",
                    }
                if (
                    isinstance(items, bool)
                    or not isinstance(items, int)
                    or not 1 <= items <= 100
                ):
                    return {
                        "status": "error",
                        "error": "itemsPerPage must be an integer between 1 and 100",
                        "parameter": "itemsPerPage",
                    }
                arguments = dict(arguments)
                arguments["page"] = page
                arguments["itemsPerPage"] = items

            if self.tool_config.get("fields", {}).get("pagination") == "dailymed_page":
                props = self.tool_config.get("parameter", {}).get("properties", {})
                page = arguments.get("page", props.get("page", {}).get("default", 1))
                pagesize = arguments.get(
                    "pagesize", props.get("pagesize", {}).get("default", 100)
                )
                if isinstance(page, bool) or not isinstance(page, int) or page < 1:
                    return {
                        "status": "error",
                        "error": "page must be an integer greater than or equal to 1",
                        "parameter": "page",
                    }
                if (
                    isinstance(pagesize, bool)
                    or not isinstance(pagesize, int)
                    or not 1 <= pagesize <= 100
                ):
                    return {
                        "status": "error",
                        "error": "pagesize must be an integer between 1 and 100",
                        "parameter": "pagesize",
                    }
                arguments = dict(arguments)
                arguments["page"] = page
                arguments["pagesize"] = pagesize

            if (
                self.tool_config.get("fields", {}).get("pagination")
                == "dataverse_start"
            ):
                props = self.tool_config.get("parameter", {}).get("properties", {})
                per_page = arguments.get(
                    "per_page", props.get("per_page", {}).get("default", 10)
                )
                start = arguments.get("start", props.get("start", {}).get("default", 0))
                item_type = arguments.get("type")
                if (
                    isinstance(per_page, bool)
                    or not isinstance(per_page, int)
                    or not 1 <= per_page <= 1000
                ):
                    return {
                        "status": "error",
                        "error": "per_page must be an integer between 1 and 1000",
                        "parameter": "per_page",
                    }
                if isinstance(start, bool) or not isinstance(start, int) or start < 0:
                    return {
                        "status": "error",
                        "error": "start must be a non-negative integer",
                        "parameter": "start",
                    }
                if item_type is not None and item_type not in {
                    "dataset",
                    "file",
                    "dataverse",
                }:
                    return {
                        "status": "error",
                        "error": "type must be one of: dataset, file, dataverse",
                        "parameter": "type",
                    }
                arguments = dict(arguments)
                arguments["per_page"] = per_page
                arguments["start"] = start

            if (
                self.tool_config.get("fields", {}).get("pagination")
                == "openfoodfacts_page"
            ):
                props = self.tool_config.get("parameter", {}).get("properties", {})
                page = arguments.get("page", props.get("page", {}).get("default", 1))
                page_size = arguments.get(
                    "page_size", props.get("page_size", {}).get("default", 10)
                )
                if isinstance(page, bool) or not isinstance(page, int) or page < 1:
                    return {
                        "status": "error",
                        "error": "page must be an integer greater than or equal to 1",
                        "parameter": "page",
                    }
                if (
                    isinstance(page_size, bool)
                    or not isinstance(page_size, int)
                    or not 1 <= page_size <= 100
                ):
                    return {
                        "status": "error",
                        "error": "page_size must be an integer between 1 and 100",
                        "parameter": "page_size",
                    }
                arguments = dict(arguments)
                arguments["page"] = page
                arguments["page_size"] = page_size

            if self.tool_config.get("fields", {}).get("pagination") == "epmc_page":
                props = self.tool_config.get("parameter", {}).get("properties", {})
                page = arguments.get("page", props.get("page", {}).get("default", 1))
                size_key = "pageSize" if "pageSize" in props else "page_size"
                page_size = arguments.get(
                    size_key, props.get(size_key, {}).get("default", 25)
                )
                if isinstance(page, bool) or not isinstance(page, int) or page < 1:
                    return {
                        "status": "error",
                        "error": "page must be an integer greater than or equal to 1",
                        "parameter": "page",
                    }
                if (
                    isinstance(page_size, bool)
                    or not isinstance(page_size, int)
                    or not 1 <= page_size <= 1000
                ):
                    return {
                        "status": "error",
                        "error": f"{size_key} must be an integer between 1 and 1000",
                        "parameter": size_key,
                    }
                arguments = dict(arguments)
                arguments["page"] = page
                arguments[size_key] = page_size

            if self.tool_config.get("fields", {}).get("pagination") == "who_odata_skip":
                props = self.tool_config.get("parameter", {}).get("properties", {})
                top_prop = props.get("top", {})
                top = arguments.get("top", top_prop.get("default", 20))
                skip = arguments.get("skip", props.get("skip", {}).get("default", 0))
                maximum = top_prop.get("maximum", 1000)
                if top is None:
                    top = top_prop.get("default", 20)
                if (
                    isinstance(top, bool)
                    or not isinstance(top, int)
                    or not 1 <= top <= maximum
                ):
                    return {
                        "status": "error",
                        "error": f"top must be an integer between 1 and {maximum}",
                        "parameter": "top",
                    }
                if isinstance(skip, bool) or not isinstance(skip, int) or skip < 0:
                    return {
                        "status": "error",
                        "error": "skip must be a non-negative integer",
                        "parameter": "skip",
                    }
                arguments = dict(arguments)
                arguments["top"] = top
                arguments["skip"] = skip

            # Normalize case-sensitive params before building the request.
            # Some backends (e.g. CPIC's PostgREST `name=eq.{name}` filter) only
            # match lowercase values, so a capitalized input silently returns an
            # empty success. `fields.lowercase_params` lists params to downcase.
            lowercase_params = (
                self.tool_config.get("fields", {}).get("lowercase_params") or []
            )
            if lowercase_params:
                arguments = dict(arguments)
                for key in lowercase_params:
                    value = arguments.get(key)
                    if isinstance(value, str):
                        arguments[key] = value.lower()

            # Fix-R30E-3: the mirror-image case -- CPIC's gene/allele tables
            # store symbols uppercase (e.g. "CYP2D6"), so a lowercase or
            # mixed-case input to `symbol=eq.{symbol}`/`genesymbol=eq.{...}`
            # silently returns an empty success (confirmed live: "cyp2d6" ->
            # 0 rows, "CYP2D6" -> 1). `fields.uppercase_params` lists params
            # to upcase.
            uppercase_params = (
                self.tool_config.get("fields", {}).get("uppercase_params") or []
            )
            if uppercase_params:
                arguments = dict(arguments)
                for key in uppercase_params:
                    value = arguments.get(key)
                    if isinstance(value, str):
                        arguments[key] = value.upper()

            url = self._build_url(arguments)
            params = self._build_params(arguments)

            # Get custom headers from config (e.g., Accept: application/json)
            custom_headers = dict(
                self.tool_config.get("fields", {}).get("headers") or {}
            )

            # Inject an API key from a request credential (or environment fallback).
            # Config: {"env_var": "MY_API_KEY", "header": "x-api-key", "required": true}.
            auth_header_cfg = self.tool_config.get("fields", {}).get("auth_header")
            api_key = ""
            if auth_header_cfg:
                env_var = auth_header_cfg.get("env_var", "")
                header_name = auth_header_cfg.get("header", "")
                api_key = self.credential(env_var)
                if not api_key and auth_header_cfg.get("required", True):
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
                            f"Provide {env_var} as a request credential or set the "
                            f"environment variable.{register_hint}"
                        ),
                    }
                if api_key:
                    custom_headers[header_name] = api_key

            rate_limit_cfg = self.tool_config.get("fields", {}).get("rate_limit")
            if rate_limit_cfg:
                credential_name = rate_limit_cfg.get("credential", "")
                rate_limit_credential = (
                    api_key
                    if auth_header_cfg
                    and credential_name == auth_header_cfg.get("env_var")
                    else self.credential(credential_name) or ""
                ) or ""
                requests_per_second = rate_limit_cfg.get(
                    "authenticated_rps" if rate_limit_credential else "anonymous_rps"
                )
                enforce_provider_rate_limit(
                    rate_limit_cfg.get("provider", self.api_name),
                    rate_limit_credential,
                    requests_per_second,
                )

            if (
                self.tool_config.get("fields", {}).get("pagination")
                == "usgs_offset_count"
            ):
                count_url = self.tool_config.get("fields", {}).get("count_endpoint")
                count_params = {
                    key: value
                    for key, value in params.items()
                    if key not in {"format", "limit", "offset", "orderby"}
                }
                try:
                    count_response = request_with_retry(
                        self.session,
                        "GET",
                        count_url,
                        params=count_params,
                        headers=custom_headers,
                        timeout=self.timeout,
                        max_attempts=3,
                    )
                    if 200 <= count_response.status_code < 300:
                        usgs_total = int((count_response.text or "").strip())
                    else:
                        usgs_count_error = f"HTTP {count_response.status_code}"
                except (TypeError, ValueError, requests.RequestException) as exc:
                    usgs_count_error = str(exc)

            if self.tool_config.get("fields", {}).get("pagination") == "erddap_page":
                import re

                html_url = url.replace("/index.json", "/index.html")
                try:
                    count_response = request_with_retry(
                        self.session,
                        "GET",
                        html_url,
                        params=params,
                        headers=custom_headers,
                        timeout=self.timeout,
                        max_attempts=3,
                    )
                    match = re.search(
                        r"([\d,]+)\s+matching datasets", count_response.text or ""
                    )
                    if 200 <= count_response.status_code < 300 and match:
                        erddap_total = int(match.group(1).replace(",", ""))
                    else:
                        erddap_count_error = (
                            f"HTTP {count_response.status_code} or count marker missing"
                        )
                except (TypeError, ValueError, requests.RequestException) as exc:
                    erddap_count_error = str(exc)

            response = request_with_retry(
                self.session,
                "GET",
                url,
                params=params,
                headers=custom_headers,
                timeout=self.timeout,
                max_attempts=3,
            )

            # The echoed `url` is the endpoint only -- query params live in
            # `params` and never appear in it, so a caller cannot tell what was
            # actually requested (which page? which filter? which $top?) and
            # cannot reproduce the call. `fields.echo_request_url` opts a tool
            # into echoing the fully-resolved request URI instead. Guarded with
            # getattr so stubbed responses in tests stay valid.
            if self.tool_config.get("fields", {}).get("echo_request_url"):
                url = getattr(response, "url", None) or url

            # Harvard Dataverse's AWS WAF currently answers API clients with
            # an empty HTTP 202 challenge. Treating every 2xx as a successful
            # search turns this into an empty-string false success.
            if (
                self.tool_config.get("fields", {}).get("pagination")
                == "dataverse_start"
                and response.status_code == 202
            ):
                headers = getattr(response, "headers", {})
                waf_action = (
                    headers.get("x-amzn-waf-action")
                    if hasattr(headers, "get")
                    else None
                )
                return {
                    "status": "error",
                    "error": (
                        "Dataverse search was not executed because the server returned "
                        "an AWS WAF challenge (HTTP 202). Retry later or use a Dataverse "
                        "instance that permits API clients."
                    ),
                    "url": url,
                    "status_code": 202,
                    "waf_action": waf_action,
                }

            # Check for errors (accept any 2xx success status)
            if not (200 <= response.status_code < 300):
                if (
                    self.tool_config.get("fields", {}).get("pagination")
                    == "erddap_page"
                    and arguments["page"] == 1
                    and "no matching results" in (response.text or "").lower()
                ):
                    return {
                        "status": "success",
                        "data": {
                            "table": {
                                "columnNames": [],
                                "columnTypes": [],
                                "columnUnits": [],
                                "rows": [],
                            }
                        },
                        "count": 0,
                        "url": url,
                        "metadata": {
                            "returned": 0,
                            "total_results": 0,
                            "total_results_is_exact": True,
                            "page": 1,
                            "items_per_page": arguments["itemsPerPage"],
                            "total_pages": 0,
                            "has_more": False,
                            "next_page": None,
                            "truncated": False,
                            "result_set_complete": True,
                            "pagination_scope": "erddap_html_count_json_page",
                        },
                    }
                # Every config-driven tool shares this path, so both of
                # these are said here rather than in each tool.
                #
                # A Cloudflare managed challenge is named, because "API error"
                # for a 403 sends a user looking for a credential problem.
                # And a tool whose upstream is gone can still point somewhere:
                # fields.unreachable_alternatives carries a pointer when a
                # usable alternative exists but is not equivalent enough to
                # repoint to. POWO is both at once -- challenged, with its
                # names in IPNI and its taxonomy in GBIF, neither of which
                # carries its distribution text.
                challenge = cloudflare_challenge(response)
                if challenge:
                    error = f"{self.api_name} is unreachable: {challenge}."
                elif 500 <= response.status_code < 600:
                    # Name the server error. "MouseMine_search API error" for
                    # a 504 reads like a problem with the request; it is the
                    # upstream being down, and the caller's next move is to
                    # wait rather than to check their query. 7 categories in
                    # the 2026-10-04 sweep were 5xx -- 502 from SKEMPI, 503
                    # from iPTMnet and EWAS Catalog, 504 from CATH and
                    # MouseMine -- all reported with that same flat sentence.
                    error = (
                        f"{self.api_name} returned HTTP "
                        f"{response.status_code}: the service is failing on "
                        "its side, not rejecting this request"
                    )
                else:
                    # The status and the service's own reason. The bare
                    # sentence was all the weekly report could quote, so
                    # biomodels, github and modeldb failed in CI (run
                    # 37273817054), passed everywhere else, and said nothing
                    # about why: a 403 refusal, a 429 limit and a 404 read
                    # the same.
                    error = f"{self.api_name} API error (HTTP {response.status_code})"
                    reason = _upstream_reason(response)
                    if reason:
                        error = f"{error}: {redact_url_secrets(reason)}"
                alternatives = (self.tool_config.get("fields") or {}).get(
                    "unreachable_alternatives"
                )
                if response.status_code >= 400 and alternatives:
                    error = f"{error} {alternatives}"
                return {
                    "status": "error",
                    "error": error,
                    "url": url,
                    "status_code": response.status_code,
                    "detail": redact_url_secrets((response.text or "")[:500]),
                }

            # Try special endpoint handling first
            special_result = self._handle_special_endpoint(url, response, arguments)
            if special_result is not None:
                return special_result

            # Use default response processing
            result = self._process_response(response, url)

            if ebi_start_page is not None:
                start, size = ebi_start_page
                records = result.get("data")
                if not isinstance(records, list):
                    return {
                        "status": "error",
                        "error": f"{self.api_name}: expected an array response from EBI eQTL Catalogue",
                        "url": url,
                    }
                has_more = len(records) > size
                page = records[:size]
                returned = len(page)
                final_position_known = not has_more and (start == 0 or returned > 0)
                result["data"] = page
                result["count"] = returned
                result["metadata"] = {
                    "returned": returned,
                    "start": start,
                    "size": size,
                    "has_more": has_more,
                    "next_start": start + returned if has_more else None,
                    "total_results": start + returned if final_position_known else None,
                    "total_results_is_exact": final_position_known,
                    "matches_lower_bound": (
                        start + returned + (1 if has_more else 0)
                        if returned or start == 0
                        else None
                    ),
                    "truncated": start > 0 or has_more,
                    "result_set_complete": start == 0 and not has_more,
                    "pagination_method": "one_record_lookahead",
                }

            if anaconda_offset_page is not None:
                offset, limit = anaconda_offset_page
                records = result.get("data")
                if not isinstance(records, list):
                    return {
                        "status": "error",
                        "error": f"{self.api_name}: expected an array from Anaconda search",
                        "url": url,
                    }
                has_more = len(records) > limit
                page = records[:limit]
                returned = len(page)
                final_position_known = not has_more
                result["data"] = page
                result["count"] = returned
                result["metadata"] = {
                    "returned": returned,
                    "offset": offset,
                    "limit": limit,
                    "has_more": has_more,
                    "next_offset": offset + returned if has_more else None,
                    "total_results": offset + returned
                    if final_position_known
                    else None,
                    "total_results_is_exact": final_position_known,
                    "matches_lower_bound": offset + returned + (1 if has_more else 0),
                    "truncated": offset > 0 or has_more,
                    "result_set_complete": offset == 0 and not has_more,
                    "pagination_scope": "anaconda_offset_one_record_lookahead",
                }

            if (
                self.tool_config.get("fields", {}).get("pagination")
                == "eva_studies_client_sort"
            ):
                data = result.get("data")
                envelopes = data.get("response", []) if isinstance(data, dict) else []
                envelope = (
                    envelopes[0] if isinstance(envelopes, list) and envelopes else {}
                )
                records = (
                    envelope.get("result", []) if isinstance(envelope, dict) else []
                )
                if not isinstance(records, list):
                    records = []
                records = sorted(
                    records,
                    key=lambda item: (
                        str(item.get("studyId", "")).casefold()
                        if isinstance(item, dict)
                        else str(item).casefold()
                    ),
                )
                actual_total = len(records)
                reported_total = (
                    envelope.get("numTotalResults")
                    if isinstance(envelope, dict)
                    else None
                )
                total_consistent = bool(
                    isinstance(reported_total, int)
                    and not isinstance(reported_total, bool)
                    and reported_total == actual_total
                )
                offset = arguments["offset"]
                limit = arguments["limit"]
                page = records[offset : offset + limit]
                returned = len(page)
                has_more = offset + returned < actual_total
                if isinstance(envelope, dict):
                    envelope["result"] = page
                    envelope["numResults"] = returned
                result["count"] = returned
                result["metadata"] = {
                    "returned": returned,
                    "total_results": actual_total,
                    "total_results_is_exact": total_consistent,
                    "accessible_results": actual_total,
                    "reported_total_results": reported_total,
                    "upstream_total_consistent": total_consistent,
                    "offset": offset,
                    "limit": limit,
                    "has_more": has_more,
                    "next_offset": offset + returned if returned and has_more else None,
                    "truncated": offset > 0 or has_more,
                    "result_set_complete": offset == 0 and returned == actual_total,
                    "sort_key": "studyId_casefold",
                    "pagination_scope": "client_page_complete_eva_study_list",
                    "upstream_pagination_supported": False,
                    "warning": (
                        f"EVA reported {reported_total} studies but returned {actual_total}; total_results reflects accessible records."
                        if not total_consistent
                        else None
                    ),
                }

            if self.tool_config.get("fields", {}).get("pagination") == "panelapp_page":
                data = result.get("data")
                records = data.get("results", []) if isinstance(data, dict) else []
                if not isinstance(records, list):
                    records = []
                returned = len(records)
                total = data.get("count") if isinstance(data, dict) else None
                total_is_exact = isinstance(total, int) and not isinstance(total, bool)
                next_url = data.get("next") if isinstance(data, dict) else None
                has_more = isinstance(next_url, str) and bool(next_url)
                page = arguments["page"]
                result["metadata"] = {
                    "returned": returned,
                    "total_results": total if total_is_exact else None,
                    "total_results_is_exact": total_is_exact,
                    "page": page,
                    "has_more": has_more,
                    "next_page": page + 1 if has_more else None,
                    "next_url": next_url if has_more else None,
                    "truncated": page > 1 or has_more,
                    "result_set_complete": bool(
                        total_is_exact
                        and page == 1
                        and not has_more
                        and returned == total
                    ),
                    "pagination_scope": "panelapp_page_next_link",
                }

            if self.tool_config.get("fields", {}).get("pagination") == "litvar_top_n":
                records = result.get("data")
                if not isinstance(records, list):
                    records = []
                returned = len(records)
                limit = arguments["limit"]
                capped = returned >= limit
                result["metadata"] = {
                    "returned": returned,
                    "requested_limit": limit,
                    "result_mode": "autocomplete_top_n",
                    "total_results": None if capped else returned,
                    "total_results_is_exact": not capped,
                    "upstream_truncated": capped,
                    "pagination_supported": False,
                    "has_more": False,
                    "next_offset": None,
                    "result_set_complete": not capped,
                    "warning": (
                        "LitVar2 returned the full requested autocomplete limit. Additional candidates may exist, but the endpoint ignores offset and cannot be paginated; increase limit up to 100 or use a more specific query."
                        if capped
                        else None
                    ),
                }

            if (
                self.tool_config.get("fields", {}).get("pagination")
                == "litvar_publications_local"
            ):
                data = result.get("data")
                if not isinstance(data, dict):
                    return {
                        "status": "error",
                        "error": f"{self.api_name}: expected a publication object from LitVar2",
                        "url": url,
                    }
                pmids = data.get("pmids", [])
                pmcids = data.get("pmcids", [])
                if not isinstance(pmids, list) or not isinstance(pmcids, list):
                    return {
                        "status": "error",
                        "error": f"{self.api_name}: LitVar2 publication ID lists have an unexpected shape",
                        "url": url,
                    }
                offset = arguments["offset"]
                page_size = arguments["max"]
                total_pmids = len(pmids)
                total_pmcids = len(pmcids)
                data["pmids"] = pmids[offset : offset + page_size]
                data["pmcids"] = pmcids[offset : offset + page_size]
                data["pmcids_count"] = total_pmcids
                reported_pmids = data.get("pmids_count")
                pmid_total_consistent = (
                    isinstance(reported_pmids, int)
                    and not isinstance(reported_pmids, bool)
                    and reported_pmids == total_pmids
                )
                has_more = (
                    offset + page_size < total_pmids
                    or offset + page_size < total_pmcids
                )
                result["count"] = max(len(data["pmids"]), len(data["pmcids"]))
                result["metadata"] = {
                    "returned_pmids": len(data["pmids"]),
                    "returned_pmcids": len(data["pmcids"]),
                    "total_pmids": total_pmids,
                    "total_pmcids": total_pmcids,
                    "totals_are_exact": True,
                    "reported_pmids_count": reported_pmids,
                    "reported_pmids_count_consistent": pmid_total_consistent,
                    "offset": offset,
                    "max": page_size,
                    "has_more": has_more,
                    "next_offset": offset + page_size if has_more else None,
                    "truncated": offset > 0 or has_more,
                    "result_set_complete": (
                        offset == 0
                        and len(data["pmids"]) == total_pmids
                        and len(data["pmcids"]) == total_pmcids
                    ),
                    "pagination_scope": "client_side_complete_litvar_publication_lists",
                    "upstream_supports_pagination": False,
                    "warning": (
                        "LitVar2 ignores max/limit/offset and returns its complete publication lists; this tool applies offset/max locally."
                        if has_more or offset > 0
                        else None
                    ),
                }

            if (
                self.tool_config.get("fields", {}).get("pagination")
                == "idr_meta_offset"
            ):
                data = result.get("data")
                records = data.get("data", []) if isinstance(data, dict) else []
                api_meta = data.get("meta", {}) if isinstance(data, dict) else {}
                if not isinstance(records, list):
                    records = []
                if not isinstance(api_meta, dict):
                    api_meta = {}
                returned = len(records)
                total = api_meta.get("totalCount")
                total_is_exact = isinstance(total, int) and not isinstance(total, bool)
                offset = api_meta.get("offset", arguments["offset"])
                limit = api_meta.get("limit", arguments["limit"])
                max_limit = api_meta.get("maxLimit")
                has_more = bool(
                    total_is_exact and returned and offset + returned < total
                )
                stalled = bool(total_is_exact and not returned and offset < total)
                result["count"] = returned
                result["metadata"] = {
                    "returned": returned,
                    "total_results": total if total_is_exact else None,
                    "total_results_is_exact": total_is_exact,
                    "offset": offset,
                    "requested_offset": arguments["offset"],
                    "limit": limit,
                    "requested_limit": arguments["limit"],
                    "max_limit": max_limit,
                    "has_more": has_more,
                    "next_offset": offset + returned if has_more else None,
                    "truncated": offset > 0 or has_more or stalled,
                    "result_set_complete": bool(
                        total_is_exact and offset == 0 and returned == total
                    ),
                    "pagination_stalled": stalled,
                    "pagination_scope": "idr_omero_meta_offset_limit",
                    "warning": (
                        "IDR reported additional records but returned an empty page at this offset."
                        if stalled
                        else None
                    ),
                }

            if self.tool_config.get("fields", {}).get("pagination") == "spring_page":
                data = result.get("data")
                api_page = data.get("page", {}) if isinstance(data, dict) else {}
                embedded = data.get("_embedded", {}) if isinstance(data, dict) else {}
                collection_key = self.tool_config.get("fields", {}).get(
                    "collection_key", "namespaces"
                )
                records = (
                    embedded.get(collection_key, [])
                    if isinstance(embedded, dict)
                    else []
                )
                if not isinstance(records, list):
                    records = []
                if not isinstance(api_page, dict):
                    api_page = {}
                returned = len(records)
                total = api_page.get("totalElements")
                total_pages = api_page.get("totalPages")
                page = api_page.get("number", arguments["page"])
                size = api_page.get("size", arguments["size"])
                total_is_exact = isinstance(total, int) and not isinstance(total, bool)
                pages_is_exact = isinstance(total_pages, int) and not isinstance(
                    total_pages, bool
                )
                has_more = bool(pages_is_exact and page + 1 < total_pages)
                result["count"] = returned
                result["metadata"] = {
                    "returned": returned,
                    "total_results": total if total_is_exact else None,
                    "total_results_is_exact": total_is_exact,
                    "page": page,
                    "requested_page": arguments["page"],
                    "size": size,
                    "requested_size": arguments["size"],
                    "total_pages": total_pages if pages_is_exact else None,
                    "has_more": has_more,
                    "next_page": page + 1 if has_more else None,
                    "truncated": page > 0 or has_more,
                    "result_set_complete": bool(
                        total_is_exact and page == 0 and returned == total
                    ),
                    "pagination_scope": "spring_data_zero_based_page",
                }

            if self.tool_config.get("fields", {}).get("pagination") == "drf_page":
                data = result.get("data")
                records = data.get("results", []) if isinstance(data, dict) else []
                if not isinstance(records, list):
                    records = []
                total = data.get("count") if isinstance(data, dict) else None
                next_url = data.get("next") if isinstance(data, dict) else None
                previous_url = data.get("previous") if isinstance(data, dict) else None
                total_is_exact = isinstance(total, int) and not isinstance(total, bool)
                page = arguments["page"]
                returned = len(records)
                page_size = self.tool_config.get("fields", {}).get("page_size", 20)
                total_pages = (
                    (total + page_size - 1) // page_size
                    if total_is_exact and page_size
                    else None
                )
                has_more = isinstance(next_url, str) and bool(next_url)
                result["count"] = returned
                result["metadata"] = {
                    "returned": returned,
                    "total_results": total if total_is_exact else None,
                    "total_results_is_exact": total_is_exact,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages,
                    "has_more": has_more,
                    "next_page": page + 1 if has_more else None,
                    "next_url": next_url if has_more else None,
                    "previous_url": previous_url,
                    "truncated": page > 1 or has_more,
                    "result_set_complete": bool(
                        total_is_exact and page == 1 and returned == total
                    ),
                    "pagination_scope": "drf_one_based_page",
                }

            if self.tool_config.get("fields", {}).get("pagination") == "dryad_hal_page":
                data = result.get("data")
                embedded = data.get("_embedded", {}) if isinstance(data, dict) else {}
                embedded_key = self.tool_config.get("fields", {}).get(
                    "hal_embedded_key", "stash:datasets"
                )
                records = (
                    embedded.get(embedded_key, []) if isinstance(embedded, dict) else []
                )
                links = data.get("_links", {}) if isinstance(data, dict) else {}
                if not isinstance(records, list):
                    records = []
                if not isinstance(links, dict):
                    links = {}
                total = data.get("total") if isinstance(data, dict) else None
                count = data.get("count") if isinstance(data, dict) else None
                total_is_exact = isinstance(total, int) and not isinstance(total, bool)
                page = arguments["page"]
                per_page = arguments["per_page"]
                returned = len(records)
                next_link = links.get("next")
                next_url = (
                    next_link.get("href") if isinstance(next_link, dict) else None
                )
                has_more = isinstance(next_url, str) and bool(next_url)
                total_pages = (
                    (total + per_page - 1) // per_page
                    if total_is_exact and per_page
                    else None
                )
                result["count"] = returned
                result["metadata"] = {
                    "returned": returned,
                    "reported_page_count": count,
                    "total_results": total if total_is_exact else None,
                    "total_results_is_exact": total_is_exact,
                    "page": page,
                    "per_page": per_page,
                    "total_pages": total_pages,
                    "has_more": has_more,
                    "next_page": page + 1 if has_more else None,
                    "next_url": next_url if has_more else None,
                    "truncated": page > 1 or has_more,
                    "result_set_complete": bool(
                        total_is_exact and page == 1 and returned == total
                    ),
                    "pagination_scope": "dryad_hal_one_based_page",
                    "embedded_record_key": embedded_key,
                }

            if self.tool_config.get("fields", {}).get("pagination") == "col_offset":
                data = result.get("data")
                records = data.get("result", []) if isinstance(data, dict) else []
                if not isinstance(records, list):
                    records = []
                reported_total = data.get("total") if isinstance(data, dict) else None
                response_offset = (
                    data.get("offset", arguments["offset"])
                    if isinstance(data, dict)
                    else arguments["offset"]
                )
                response_limit = (
                    data.get("limit", arguments["limit"])
                    if isinstance(data, dict)
                    else arguments["limit"]
                )
                returned = len(records)
                total_well_formed = isinstance(reported_total, int) and not isinstance(
                    reported_total, bool
                )
                # CoL raises `total` to the requested offset on an empty page
                # beyond the real end (e.g. a nonexistent parent at offset 2
                # reports total=2). A non-empty page, or the first page, is the
                # only evidence that its total is the actual collection total.
                total_is_exact = bool(
                    total_well_formed and (returned > 0 or response_offset == 0)
                )
                total = reported_total if total_is_exact else None
                has_more = bool(
                    total_is_exact
                    and returned
                    and response_offset + returned < reported_total
                )
                result["count"] = returned
                result["metadata"] = {
                    "returned": returned,
                    "total_results": total,
                    "total_results_is_exact": total_is_exact,
                    "reported_total_results": reported_total,
                    "offset": response_offset,
                    "requested_offset": arguments["offset"],
                    "limit": response_limit,
                    "requested_limit": arguments["limit"],
                    "has_more": has_more,
                    "next_offset": response_offset + returned if has_more else None,
                    "truncated": response_offset > 0 or has_more,
                    "result_set_complete": bool(
                        total_is_exact and response_offset == 0 and returned == total
                    ),
                    "pagination_scope": "catalogue_of_life_offset_limit",
                    "warning": (
                        "Catalogue of Life can inflate total to the requested offset on an empty deep page; this response's reported total was not treated as exact."
                        if total_well_formed and not total_is_exact
                        else None
                    ),
                }

            if self.tool_config.get("fields", {}).get("pagination") == "biotools_page":
                data = result.get("data")
                records = data.get("list", []) if isinstance(data, dict) else []
                total = data.get("count") if isinstance(data, dict) else None
                upstream_next = data.get("next") if isinstance(data, dict) else None
                upstream_previous = (
                    data.get("previous") if isinstance(data, dict) else None
                )
                if not isinstance(records, list):
                    records = []
                total_is_exact = isinstance(total, int) and not isinstance(total, bool)
                page = arguments["page"]
                size = arguments["size"]
                returned = len(records)
                total_pages = (
                    (total + size - 1) // size if total_is_exact and size else None
                )
                has_more = bool(total_is_exact and returned and page * size < total)
                continuation = {
                    key: value
                    for key, value in arguments.items()
                    if key not in {"page", "size"} and value is not None
                }
                continuation.update({"page": page + 1, "per_page": size})
                next_url = (
                    self.tool_config["fields"]["endpoint"]
                    + "?"
                    + urllib.parse.urlencode(continuation)
                    if has_more
                    else None
                )
                if isinstance(data, dict):
                    data["next"] = next_url
                result["count"] = returned
                result["metadata"] = {
                    "returned": returned,
                    "total_results": total if total_is_exact else None,
                    "total_results_is_exact": total_is_exact,
                    "page": page,
                    "size": size,
                    "total_pages": total_pages,
                    "has_more": has_more,
                    "next_page": page + 1 if has_more else None,
                    "next_url": next_url,
                    "continuation_parameters": continuation if has_more else None,
                    "upstream_next": upstream_next,
                    "upstream_previous": upstream_previous,
                    "upstream_links_drop_filters": bool(
                        has_more
                        and isinstance(upstream_next, str)
                        and "q=" not in upstream_next
                        and not any(
                            f"{key}=" in upstream_next
                            for key in ("topic", "operation", "toolType")
                        )
                    ),
                    "truncated": page > 1 or has_more,
                    "result_set_complete": bool(
                        total_is_exact and page == 1 and returned == total
                    ),
                    "pagination_scope": "biotools_one_based_page",
                }

            if self.tool_config.get("fields", {}).get("pagination") == "eonet_top_n":
                data = result.get("data")
                events = data.get("events", []) if isinstance(data, dict) else []
                if not isinstance(events, list):
                    return {
                        "status": "error",
                        "error": f"{self.api_name}: expected an events array from NASA EONET",
                        "url": url,
                    }
                limit = eonet_requested_limit
                has_additional = len(events) > limit
                page = events[:limit]
                returned = len(page)
                if isinstance(data, dict):
                    data["events"] = page
                result["count"] = returned
                result["metadata"] = {
                    "returned": returned,
                    "requested_limit": limit,
                    "total_results": None if has_additional else returned,
                    "total_results_is_exact": not has_additional,
                    "matches_lower_bound": limit + 1 if has_additional else returned,
                    "upstream_truncated": has_additional,
                    "pagination_supported": False,
                    "has_more": False,
                    "next_offset": None,
                    "truncated": has_additional,
                    "result_set_complete": not has_additional,
                    "pagination_scope": "eonet_top_n_one_record_lookahead",
                    "warning": (
                        "NASA EONET matched more events than the requested top-N limit but exposes no offset/cursor. Narrow status/category/date/bbox filters or increase limit up to 1000."
                        if has_additional
                        else None
                    ),
                }

            if self.tool_config.get("fields", {}).get("pagination") == "dataone_solr":
                data = result.get("data")
                response_data = (
                    data.get("response", {}) if isinstance(data, dict) else {}
                )
                docs = (
                    response_data.get("docs", [])
                    if isinstance(response_data, dict)
                    else []
                )
                if not isinstance(docs, list):
                    docs = []
                total = (
                    response_data.get("numFound")
                    if isinstance(response_data, dict)
                    else None
                )
                response_start = (
                    response_data.get("start", arguments["start"])
                    if isinstance(response_data, dict)
                    else arguments["start"]
                )
                returned = len(docs)
                total_is_exact = isinstance(total, int) and not isinstance(total, bool)
                has_more = bool(
                    total_is_exact and returned and response_start + returned < total
                )
                stalled = bool(
                    total_is_exact and not returned and response_start < total
                )
                result["count"] = returned
                result["metadata"] = {
                    "returned": returned,
                    "total_results": total if total_is_exact else None,
                    "total_results_is_exact": total_is_exact,
                    "start": response_start,
                    "requested_start": arguments["start"],
                    "rows": arguments["rows"],
                    "has_more": has_more,
                    "next_start": response_start + returned if has_more else None,
                    "truncated": response_start > 0 or has_more or stalled,
                    "result_set_complete": bool(
                        total_is_exact and response_start == 0 and returned == total
                    ),
                    "pagination_stalled": stalled,
                    "pagination_scope": "dataone_solr_start_rows_numFound",
                    "warning": (
                        "DataONE reported additional records but returned an empty page at this start offset."
                        if stalled
                        else None
                    ),
                }

            if self.tool_config.get("fields", {}).get("pagination") == "ceda_offset":
                data = result.get("data")
                records = data.get("results", []) if isinstance(data, dict) else []
                total = data.get("count") if isinstance(data, dict) else None
                next_url = data.get("next") if isinstance(data, dict) else None
                previous_url = data.get("previous") if isinstance(data, dict) else None
                if not isinstance(records, list):
                    records = []
                returned = len(records)
                total_is_exact = isinstance(total, int) and not isinstance(total, bool)
                offset = arguments["offset"]
                limit = arguments["limit"]
                has_more = bool(
                    total_is_exact and returned and offset + returned < total
                )
                result["count"] = returned
                result["metadata"] = {
                    "returned": returned,
                    "total_results": total if total_is_exact else None,
                    "total_results_is_exact": total_is_exact,
                    "offset": offset,
                    "limit": limit,
                    "has_more": has_more,
                    "next_offset": offset + returned if has_more else None,
                    "next_url": next_url if has_more else None,
                    "previous_url": previous_url,
                    "truncated": offset > 0 or has_more,
                    "result_set_complete": bool(
                        total_is_exact and offset == 0 and returned == total
                    ),
                    "pagination_scope": "ceda_django_icontains_offset_limit",
                    "applied_search_filter": next(
                        (key for key in arguments if key.endswith("__icontains")),
                        None,
                    ),
                }

            if self.tool_config.get("fields", {}).get("pagination") == "erddap_page":
                data = result.get("data")
                table = data.get("table", {}) if isinstance(data, dict) else {}
                rows = table.get("rows", []) if isinstance(table, dict) else []
                if not isinstance(rows, list):
                    rows = []
                returned = len(rows)
                page = arguments["page"]
                items = arguments["itemsPerPage"]
                total_is_exact = isinstance(erddap_total, int) and not isinstance(
                    erddap_total, bool
                )
                total_pages = (
                    (erddap_total + items - 1) // items if total_is_exact else None
                )
                has_more = bool(total_is_exact and page * items < erddap_total)
                result["count"] = returned
                result["metadata"] = {
                    "returned": returned,
                    "total_results": erddap_total if total_is_exact else None,
                    "total_results_is_exact": total_is_exact,
                    "page": page,
                    "items_per_page": items,
                    "total_pages": total_pages,
                    "has_more": has_more,
                    "next_page": page + 1 if has_more else None,
                    "truncated": page > 1 or has_more,
                    "result_set_complete": bool(
                        total_is_exact and page == 1 and returned == erddap_total
                    ),
                    "pagination_scope": "erddap_html_count_json_page",
                    "count_probe_error": erddap_count_error,
                }

            if self.tool_config.get("fields", {}).get("pagination") == "dailymed_page":
                data = result.get("data")
                records = data.get("data", []) if isinstance(data, dict) else []
                api_metadata = (
                    data.get("metadata", {}) if isinstance(data, dict) else {}
                )
                if not isinstance(records, list):
                    records = []
                if not isinstance(api_metadata, dict):
                    api_metadata = {}
                api_metadata = {
                    key: (None if value == "null" else value)
                    for key, value in api_metadata.items()
                }
                if isinstance(data, dict):
                    data["metadata"] = api_metadata
                total = api_metadata.get("total_elements")
                total_is_exact = isinstance(total, int) and not isinstance(total, bool)
                page = api_metadata.get("current_page", arguments["page"])
                pagesize = api_metadata.get("elements_per_page", arguments["pagesize"])
                next_page = api_metadata.get("next_page")
                next_url = api_metadata.get("next_page_url")
                has_more = isinstance(next_page, int) and not isinstance(
                    next_page, bool
                )
                returned = len(records)
                result["count"] = returned
                result["metadata"] = {
                    "returned": returned,
                    "total_results": total if total_is_exact else None,
                    "total_results_is_exact": total_is_exact,
                    "page": page,
                    "pagesize": pagesize,
                    "total_pages": api_metadata.get("total_pages"),
                    "has_more": has_more,
                    "next_page": next_page if has_more else None,
                    "next_url": next_url if has_more else None,
                    "previous_page": api_metadata.get("previous_page"),
                    "previous_url": api_metadata.get("previous_page_url"),
                    "truncated": page > 1 or has_more,
                    "result_set_complete": bool(
                        total_is_exact and page == 1 and returned == total
                    ),
                    "pagination_scope": "dailymed_exact_one_based_page",
                }

            if (
                self.tool_config.get("fields", {}).get("pagination")
                == "dataverse_start"
            ):
                data = result.get("data")
                records = data.get("items", []) if isinstance(data, dict) else []
                if not isinstance(records, list):
                    records = []
                total = data.get("total_count") if isinstance(data, dict) else None
                reported_start = data.get("start") if isinstance(data, dict) else None
                if isinstance(reported_start, bool) or not isinstance(
                    reported_start, int
                ):
                    reported_start = arguments["start"]
                total_is_exact = isinstance(total, int) and not isinstance(total, bool)
                returned = len(records)
                has_more = bool(
                    total_is_exact and returned and reported_start + returned < total
                )
                result["count"] = returned
                result["metadata"] = {
                    "returned": returned,
                    "reported_count_in_response": (
                        data.get("count_in_response")
                        if isinstance(data, dict)
                        else None
                    ),
                    "total_results": total if total_is_exact else None,
                    "total_results_is_exact": total_is_exact,
                    "start": reported_start,
                    "per_page": arguments["per_page"],
                    "has_more": has_more,
                    "next_start": reported_start + returned if has_more else None,
                    "truncated": reported_start > 0 or has_more,
                    "result_set_complete": bool(
                        total_is_exact and reported_start == 0 and returned == total
                    ),
                    "pagination_scope": "dataverse_exact_start_offset",
                }

            if (
                self.tool_config.get("fields", {}).get("pagination")
                == "openfoodfacts_page"
            ):
                data = result.get("data")
                records = data.get("products", []) if isinstance(data, dict) else []
                if not isinstance(records, list):
                    records = []

                def off_integer(value):
                    if isinstance(value, bool):
                        return None
                    try:
                        parsed = int(value)
                    except (TypeError, ValueError):
                        return None
                    return parsed if parsed >= 0 else None

                total = (
                    off_integer(data.get("count")) if isinstance(data, dict) else None
                )
                page = off_integer(data.get("page")) if isinstance(data, dict) else None
                if page is None:
                    page = arguments["page"]
                effective_size = (
                    off_integer(data.get("page_size"))
                    if isinstance(data, dict)
                    else None
                )
                if not effective_size:
                    effective_size = arguments["page_size"]
                returned = len(records)
                total_is_exact = total is not None
                total_pages = (
                    (total + effective_size - 1) // effective_size
                    if total_is_exact and effective_size
                    else None
                )
                has_more = bool(
                    total_is_exact and returned and page * effective_size < total
                )
                result["count"] = returned
                result["metadata"] = {
                    "returned": returned,
                    "upstream_page_count": (
                        off_integer(data.get("page_count"))
                        if isinstance(data, dict)
                        else None
                    ),
                    "upstream_page_count_semantics": "records_on_current_page",
                    "total_results": total,
                    "total_results_is_exact": total_is_exact,
                    "page": page,
                    "page_size": effective_size,
                    "total_pages": total_pages,
                    "has_more": has_more,
                    "next_page": page + 1 if has_more else None,
                    "truncated": page > 1 or has_more,
                    "result_set_complete": bool(
                        total_is_exact and page == 1 and returned == total
                    ),
                    "pagination_scope": "openfoodfacts_count_one_based_page",
                }

            if self.tool_config.get("fields", {}).get("pagination") == "epmc_page":
                data = result.get("data")
                fields = self.tool_config.get("fields", {})
                container_key = fields.get("record_container")
                record_key = fields.get("record_key")
                container = data.get(container_key) if isinstance(data, dict) else None
                records = (
                    container.get(record_key, []) if isinstance(container, dict) else []
                )
                if not isinstance(records, list):
                    records = []
                total = data.get("hitCount") if isinstance(data, dict) else None
                total_is_exact = isinstance(total, int) and not isinstance(total, bool)
                page = arguments["page"]
                page_size = arguments.get("pageSize", arguments.get("page_size", 25))
                returned = len(records)
                consumed = (page - 1) * page_size + returned
                has_more = bool(total_is_exact and returned and consumed < total)
                result["count"] = returned
                result["metadata"] = {
                    "returned": returned,
                    "total_results": total if total_is_exact else None,
                    "total_results_is_exact": total_is_exact,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": (
                        (total + page_size - 1) // page_size if total_is_exact else None
                    ),
                    "has_more": has_more,
                    "next_page": page + 1 if has_more else None,
                    "truncated": page > 1 or has_more,
                    "result_set_complete": bool(
                        total_is_exact and page == 1 and returned == total
                    ),
                    "record_path": f"{container_key}.{record_key}",
                    "pagination_scope": "europe_pmc_hitcount_one_based_page",
                }

            if self.tool_config.get("fields", {}).get("pagination") == "who_odata_skip":
                data = result.get("data")
                records = data.get("value", []) if isinstance(data, dict) else []
                if not isinstance(records, list):
                    records = []
                returned = len(records)
                total = data.get("@odata.count") if isinstance(data, dict) else None
                total_is_exact = isinstance(total, int) and not isinstance(total, bool)
                skip = arguments["skip"]
                top = arguments["top"]
                has_more = bool(total_is_exact and returned and skip + returned < total)
                stalled = bool(total_is_exact and not returned and skip < total)
                result["metadata"] = {
                    "returned": returned,
                    "total_results": total if total_is_exact else None,
                    "total_results_is_exact": total_is_exact,
                    "skip": skip,
                    "top": top,
                    "has_more": has_more,
                    "next_skip": skip + returned if has_more else None,
                    "truncated": skip > 0 or has_more,
                    "result_set_complete": bool(
                        total_is_exact and skip == 0 and returned == total
                    ),
                    "pagination_stalled": stalled,
                    "pagination_scope": "who_gho_odata_skip_count",
                    "warning": (
                        "WHO GHO reported additional records but returned an empty page at this skip."
                        if stalled
                        else None
                    ),
                }

            if (
                self.tool_config.get("fields", {}).get("pagination")
                == "nci_drugdict_offset"
            ):
                data = result.get("data")
                meta = data.get("meta", {}) if isinstance(data, dict) else {}
                records = data.get("results", []) if isinstance(data, dict) else []
                if not isinstance(records, list):
                    records = []
                returned = len(records)
                total = meta.get("totalResults")
                total_is_exact = isinstance(total, int) and not isinstance(total, bool)
                offset_key = self.tool_config.get("fields", {}).get(
                    "offset_parameter", "offset"
                )
                requested_offset = arguments.get(offset_key, 0)
                offset = meta.get("from", requested_offset)
                if isinstance(offset, bool) or not isinstance(offset, int):
                    offset = requested_offset
                has_more = bool(
                    total_is_exact and returned and offset + returned < total
                )
                stalled = bool(total_is_exact and not returned and offset < total)
                result["metadata"] = {
                    "returned": returned,
                    "total_results": total if total_is_exact else None,
                    "total_results_is_exact": total_is_exact,
                    "offset": offset,
                    "size": arguments.get("size", 10),
                    "has_more": has_more,
                    "next_offset": offset + returned if has_more else None,
                    "truncated": bool(offset > 0 or has_more or stalled),
                    "result_set_complete": bool(
                        total_is_exact and offset == 0 and returned == total
                    ),
                    "pagination_stalled": stalled,
                    "warning": (
                        "NCI reported additional matches but returned no records at this offset; refine the query."
                        if stalled
                        else None
                    ),
                }

            if self.tool_config.get("fields", {}).get("pagination") == "eva_skip":
                data = result.get("data")
                envelopes = data.get("response", []) if isinstance(data, dict) else []
                envelope = (
                    envelopes[0] if isinstance(envelopes, list) and envelopes else {}
                )
                records = (
                    envelope.get("result", []) if isinstance(envelope, dict) else []
                )
                if not isinstance(records, list):
                    records = []
                returned = len(records)
                reported_total = (
                    envelope.get("numTotalResults")
                    if isinstance(envelope, dict)
                    else None
                )
                offset = arguments.get("offset", 0)
                limit = arguments.get("limit", 20)
                reported_total_is_integer = isinstance(
                    reported_total, int
                ) and not isinstance(reported_total, bool)
                total_inconsistent = bool(
                    reported_total_is_integer and reported_total < offset + returned
                )
                upstream_total_usable = (
                    reported_total_is_integer and not total_inconsistent
                )
                if upstream_total_usable:
                    total = reported_total
                    total_is_exact = True
                    has_more = bool(returned and offset + returned < total)
                else:
                    # EVA's region endpoint has been observed returning
                    # numTotalResults=0 alongside non-empty pages. A full page
                    # is therefore continued until a short page proves the end.
                    has_more = returned == limit
                    final_position_known = not has_more and (
                        offset == 0 or returned > 0
                    )
                    total = offset + returned if final_position_known else None
                    total_is_exact = final_position_known
                stalled = bool(
                    upstream_total_usable and not returned and offset < reported_total
                )
                result["metadata"] = {
                    "returned": returned,
                    "total_results": total,
                    "total_results_is_exact": total_is_exact,
                    "upstream_total_results": reported_total,
                    "upstream_total_inconsistent": total_inconsistent,
                    "matches_lower_bound": offset + returned,
                    "offset": offset,
                    "limit": limit,
                    "has_more": has_more,
                    "next_offset": offset + returned if has_more else None,
                    "truncated": bool(offset > 0 or has_more or stalled),
                    "result_set_complete": bool(
                        total_is_exact and offset == 0 and returned == total
                    ),
                    "offset_must_align_to_limit": True,
                    "pagination_stalled": stalled,
                    "warning": (
                        "EVA reported additional variants but returned no records; keep the same limit and use metadata.next_offset, or refine the query."
                        if stalled
                        else (
                            "EVA's numTotalResults conflicts with the non-empty page and was not used; continue with next_offset until a short page establishes the exact total."
                            if total_inconsistent
                            else None
                        )
                    ),
                }

            if (
                self.tool_config.get("fields", {}).get("pagination")
                == "intermine_start"
            ):
                data = result.get("data")
                records = data.get("results", []) if isinstance(data, dict) else []
                if not isinstance(records, list):
                    records = []
                returned = len(records)
                total = data.get("totalHits") if isinstance(data, dict) else None
                total_is_exact = isinstance(total, int) and not isinstance(total, bool)
                start = arguments.get("start", 0)
                size = arguments.get("size", 10)
                has_more = bool(
                    total_is_exact and returned and start + returned < total
                )
                stalled = bool(total_is_exact and not returned and start < total)
                result["metadata"] = {
                    "returned": returned,
                    "total_results": total if total_is_exact else None,
                    "total_results_is_exact": total_is_exact,
                    "start": start,
                    "size": size,
                    "has_more": has_more,
                    "next_start": start + returned if has_more else None,
                    "truncated": bool(start > 0 or has_more or stalled),
                    "result_set_complete": bool(
                        total_is_exact and start == 0 and returned == total
                    ),
                    "pagination_stalled": stalled,
                    "warning": (
                        "InterMine reported additional hits but returned no records at this start offset; refine the query."
                        if stalled
                        else None
                    ),
                }

            if (
                self.tool_config.get("fields", {}).get("pagination")
                == "client_side_offset"
            ):
                records = result.get("data")
                if not isinstance(records, list):
                    return {
                        "status": "error",
                        "error": f"{self.api_name}: expected an array for client-side pagination",
                        "url": url,
                    }
                total = len(records)
                offset = arguments.get("offset", 0)
                limit = arguments.get("limit", 100)
                page = records[offset : offset + limit]
                returned = len(page)
                has_more = offset + returned < total
                result["data"] = page
                result["count"] = returned
                result["total_before_limit"] = total
                result["metadata"] = {
                    "returned": returned,
                    "total_results": total,
                    "total_results_is_exact": True,
                    "offset": offset,
                    "limit": limit,
                    "has_more": has_more,
                    "next_offset": offset + returned if returned and has_more else None,
                    "truncated": offset > 0 or has_more,
                    "result_set_complete": offset == 0 and returned == total,
                    "pagination_scope": "client_side_full_response",
                    "upstream_supports_pagination": False,
                }

            if (
                self.tool_config.get("fields", {}).get("pagination")
                == "huggingface_cursor"
            ):
                import re

                records = result.get("data")
                if not isinstance(records, list):
                    return {
                        "status": "error",
                        "error": f"{self.api_name}: expected an array from Hugging Face Hub",
                        "url": url,
                    }
                link = response.headers.get("Link", "")
                next_cursor = None
                for target, relation in re.findall(
                    r'<([^>]+)>\s*;\s*rel=["\']?([^"\';,]+)', link
                ):
                    if relation == "next":
                        values = urllib.parse.parse_qs(
                            urllib.parse.urlparse(target).query
                        ).get("cursor", [])
                        next_cursor = values[0] if values else None
                        break
                returned = len(records)
                has_more = bool(next_cursor)
                result["metadata"] = {
                    "returned": returned,
                    "limit": arguments.get("limit", 20),
                    "has_more": has_more,
                    "next_cursor": next_cursor,
                    "total_results": None,
                    "total_results_is_exact": False,
                    "matches_lower_bound": returned + (1 if has_more else 0),
                    "truncated": bool(arguments.get("cursor") or has_more),
                    "result_set_complete": not arguments.get("cursor") and not has_more,
                    "pagination_scope": "upstream_opaque_cursor",
                }

            if (
                self.tool_config.get("fields", {}).get("pagination")
                == "semantic_scholar_offset"
            ):
                data = result.get("data")
                records = data.get("data", []) if isinstance(data, dict) else []
                if not isinstance(records, list):
                    records = []
                returned = len(records)
                total = data.get("total") if isinstance(data, dict) else None
                total_is_exact = isinstance(total, int) and not isinstance(total, bool)
                upstream_offset = data.get("offset") if isinstance(data, dict) else None
                offset = (
                    upstream_offset
                    if isinstance(upstream_offset, int)
                    and not isinstance(upstream_offset, bool)
                    else arguments.get("offset", 0)
                )
                upstream_next = data.get("next") if isinstance(data, dict) else None
                next_offset = (
                    upstream_next
                    if isinstance(upstream_next, int)
                    and not isinstance(upstream_next, bool)
                    else None
                )
                has_more = next_offset is not None
                if not total_is_exact and not has_more:
                    # Offset endpoints that omit `total` still establish their
                    # exact length on the terminal page.
                    total = offset + returned
                    total_is_exact = True
                result["metadata"] = {
                    "returned": returned,
                    "total_results": total if total_is_exact else None,
                    "total_results_is_exact": total_is_exact,
                    "matches_lower_bound": (
                        total
                        if total_is_exact
                        else offset + returned + (1 if has_more else 0)
                    ),
                    "offset": offset,
                    "limit": arguments.get("limit"),
                    "has_more": has_more,
                    "next_offset": next_offset,
                    "truncated": offset > 0 or has_more,
                    "result_set_complete": bool(
                        total_is_exact and offset == 0 and returned == total
                    ),
                    "pagination_scope": "upstream_offset_next",
                }

            if self.tool_config.get("fields", {}).get("pagination") == "runiverse_skip":
                data = result.get("data")
                records = data.get("results", []) if isinstance(data, dict) else []
                if not isinstance(records, list):
                    records = []
                returned = len(records)
                total = data.get("total") if isinstance(data, dict) else None
                total_is_exact = isinstance(total, int) and not isinstance(total, bool)
                offset = (
                    data.get("skip", arguments.get("offset", 0))
                    if isinstance(data, dict)
                    else arguments.get("offset", 0)
                )
                limit = (
                    data.get("limit", arguments.get("limit", 10))
                    if isinstance(data, dict)
                    else arguments.get("limit", 10)
                )
                has_more = bool(
                    total_is_exact and returned and offset + returned < total
                )
                result["metadata"] = {
                    "returned": returned,
                    "total_results": total if total_is_exact else None,
                    "total_results_is_exact": total_is_exact,
                    "offset": offset,
                    "limit": limit,
                    "has_more": has_more,
                    "next_offset": offset + returned if has_more else None,
                    "truncated": offset > 0 or has_more,
                    "result_set_complete": bool(
                        total_is_exact and offset == 0 and returned == total
                    ),
                    "pagination_scope": "upstream_skip_total",
                }

            if self.tool_config.get("fields", {}).get("pagination") == "tess_page":
                records = result.get("data")
                if not isinstance(records, list):
                    return {
                        "status": "error",
                        "error": f"{self.api_name}: expected an array from ELIXIR TeSS",
                        "url": url,
                    }
                returned = len(records)
                page = arguments.get("page", 1)
                page_size = arguments.get("page_size", 10)
                has_more = returned == page_size
                final_position_known = not has_more and (page == 1 or returned > 0)
                total = (
                    (page - 1) * page_size + returned if final_position_known else None
                )
                result["metadata"] = {
                    "returned": returned,
                    "page": page,
                    "page_size": page_size,
                    "has_more": has_more,
                    "next_page": page + 1 if has_more else None,
                    "total_results": total,
                    "total_results_is_exact": final_position_known,
                    "matches_lower_bound": (page - 1) * page_size + returned,
                    "truncated": page > 1 or has_more,
                    "result_set_complete": page == 1 and not has_more,
                    "pagination_scope": "upstream_one_based_full_page_continuation",
                }

            if (
                self.tool_config.get("fields", {}).get("pagination")
                == "openml_offset_path"
            ):
                data = result.get("data")
                container = data.get("data", {}) if isinstance(data, dict) else {}
                records = (
                    container.get("dataset", []) if isinstance(container, dict) else []
                )
                if not isinstance(records, list):
                    records = []
                returned = len(records)
                limit = arguments.get("limit", 20)
                offset = arguments.get("offset", 0)
                has_more = returned == limit
                final_position_known = not has_more and (offset == 0 or returned > 0)
                result["metadata"] = {
                    "returned": returned,
                    "limit": limit,
                    "offset": offset,
                    "has_more": has_more,
                    "next_offset": offset + returned if has_more else None,
                    "total_results": offset + returned
                    if final_position_known
                    else None,
                    "total_results_is_exact": final_position_known,
                    "matches_lower_bound": offset + returned,
                    "truncated": offset > 0 or has_more,
                    "result_set_complete": offset == 0 and not has_more,
                    "pagination_scope": "upstream_offset_full_page_continuation",
                }

            if self.tool_config.get("fields", {}).get("pagination") == "cmr_page":
                data = result.get("data")
                feed = data.get("feed", {}) if isinstance(data, dict) else {}
                records = feed.get("entry", []) if isinstance(feed, dict) else []
                if not isinstance(records, list):
                    records = []
                returned = len(records)
                try:
                    total = int(response.headers.get("CMR-Hits", ""))
                    total_is_exact = total >= 0
                except (TypeError, ValueError):
                    total = None
                    total_is_exact = False
                page = arguments.get("page", 1)
                page_size = arguments.get("page_size", 10)
                consumed = (page - 1) * page_size + returned
                has_more = bool(total_is_exact and returned and consumed < total)
                result["metadata"] = {
                    "returned": returned,
                    "total_results": total if total_is_exact else None,
                    "total_results_is_exact": total_is_exact,
                    "page": page,
                    "page_size": page_size,
                    "has_more": has_more,
                    "next_page": page + 1 if has_more else None,
                    "truncated": page > 1 or has_more,
                    "result_set_complete": bool(
                        total_is_exact and page == 1 and returned == total
                    ),
                    "pagination_scope": "upstream_cmr_hits_page_num",
                }

            if self.tool_config.get("fields", {}).get("pagination") == "inspire_page":
                data = result.get("data")
                hits = data.get("hits", {}) if isinstance(data, dict) else {}
                records = hits.get("hits", []) if isinstance(hits, dict) else []
                if not isinstance(records, list):
                    records = []
                returned = len(records)
                total = hits.get("total") if isinstance(hits, dict) else None
                total_is_exact = isinstance(total, int) and not isinstance(total, bool)
                page = arguments.get("page", 1)
                size = arguments.get("size", 10)
                consumed = (page - 1) * size + returned
                has_more = bool(total_is_exact and returned and consumed < total)
                result["metadata"] = {
                    "returned": returned,
                    "total_results": total if total_is_exact else None,
                    "total_results_is_exact": total_is_exact,
                    "page": page,
                    "size": size,
                    "has_more": has_more,
                    "next_page": page + 1 if has_more else None,
                    "truncated": page > 1 or has_more,
                    "result_set_complete": bool(
                        total_is_exact and page == 1 and returned == total
                    ),
                    "pagination_scope": "upstream_page_hits_total",
                }

            if (
                self.tool_config.get("fields", {}).get("pagination")
                == "worldbank_indicator_search"
            ):
                data = result.get("data")
                if (
                    not isinstance(data, list)
                    or len(data) < 2
                    or not isinstance(data[1], list)
                ):
                    return {
                        "status": "error",
                        "error": f"{self.api_name}: unexpected World Bank indicator catalog response",
                        "url": url,
                    }
                upstream_meta = data[0] if isinstance(data[0], dict) else {}
                catalog = data[1]
                tokens = arguments["query"].casefold().split()

                def searchable_text(record: Any) -> str:
                    if not isinstance(record, dict):
                        return ""
                    source = record.get("source")
                    source_name = (
                        source.get("value", "") if isinstance(source, dict) else ""
                    )
                    return (
                        " ".join(
                            str(record.get(key, ""))
                            for key in ("id", "name", "sourceNote")
                        ).casefold()
                        + " "
                        + str(source_name).casefold()
                    )

                matches = [
                    record
                    for record in catalog
                    if all(token in searchable_text(record) for token in tokens)
                ]
                offset = arguments["offset"]
                per_page = arguments["per_page"]
                page_records = matches[offset : offset + per_page]
                returned = len(page_records)
                accessible_total = len(matches)
                has_more = offset + returned < accessible_total
                upstream_total = upstream_meta.get("total")
                upstream_total_is_integer = isinstance(
                    upstream_total, int
                ) and not isinstance(upstream_total, bool)
                omitted = (
                    max(upstream_total - len(catalog), 0)
                    if upstream_total_is_integer
                    else None
                )
                upstream_truncated = bool(omitted)
                pages = (accessible_total + per_page - 1) // per_page
                local_meta = {
                    "page": offset // per_page + 1,
                    "pages": pages,
                    "per_page": per_page,
                    "total": accessible_total,
                    "query": arguments["query"],
                    "offset": offset,
                    "total_is_exact": not upstream_truncated,
                    "catalog_scope": "accessible_world_bank_indicator_catalog",
                }
                result["data"] = [local_meta, page_records]
                result["count"] = returned
                result["metadata"] = {
                    "returned": returned,
                    "accessible_matching_indicators": accessible_total,
                    "total_results": accessible_total,
                    "total_results_is_exact": not upstream_truncated,
                    "matches_lower_bound": accessible_total,
                    "offset": offset,
                    "per_page": per_page,
                    "has_more": has_more,
                    "next_offset": offset + returned if returned and has_more else None,
                    "upstream_catalog_total": upstream_total
                    if upstream_total_is_integer
                    else None,
                    "accessible_catalog_entries": len(catalog),
                    "upstream_catalog_omitted": omitted,
                    "upstream_truncated": upstream_truncated,
                    "truncated": offset > 0 or has_more or upstream_truncated,
                    "result_set_complete": bool(
                        offset == 0 and not has_more and not upstream_truncated
                    ),
                    "pagination_scope": "client_filtered_accessible_catalog",
                    "warning": (
                        f"World Bank reported {upstream_total} indicators but returned {len(catalog)} in its one-page full-catalog response; search totals exclude the {omitted} omitted catalog entries."
                        if upstream_truncated
                        else None
                    ),
                }

            if self.tool_config.get("fields", {}).get("pagination") == "artic_page":
                data = result.get("data")
                pagination = (
                    data.get("pagination", {}) if isinstance(data, dict) else {}
                )
                records = data.get("data", []) if isinstance(data, dict) else []
                if not isinstance(records, list):
                    records = []
                total = (
                    pagination.get("total") if isinstance(pagination, dict) else None
                )
                total_is_exact = isinstance(total, int) and not isinstance(total, bool)
                returned = len(records)
                page = arguments["page"]
                limit = arguments["limit"]
                current_page = pagination.get("current_page")
                total_pages = pagination.get("total_pages")
                has_more = bool(
                    returned
                    and isinstance(current_page, int)
                    and isinstance(total_pages, int)
                    and current_page < total_pages
                )
                result["metadata"] = {
                    "returned": returned,
                    "ranked_catalog_candidates": total if total_is_exact else None,
                    "total_results": total if total_is_exact else None,
                    "total_results_is_exact": total_is_exact,
                    "total_count_scope": "ranked_catalog_candidates_not_exact_text_matches",
                    "page": page,
                    "limit": limit,
                    "has_more": has_more,
                    "next_page": page + 1 if has_more else None,
                    "truncated": page > 1 or has_more,
                    "result_set_complete": bool(
                        total_is_exact and page == 1 and returned == total
                    ),
                    "pagination_scope": "upstream_page_ranked_catalog",
                    "warning": (
                        "ArtIC q ranks the full searchable catalog, including very low-score records; total_results is the ranked candidate count, not a count of exact keyword matches."
                    ),
                }

            if (
                self.tool_config.get("fields", {}).get("pagination")
                == "github_search_page"
            ):
                data = result.get("data")
                items = data.get("items", []) if isinstance(data, dict) else []
                if not isinstance(items, list):
                    items = []
                total = data.get("total_count") if isinstance(data, dict) else None
                total_is_integer = isinstance(total, int) and not isinstance(
                    total, bool
                )
                incomplete = (
                    bool(data.get("incomplete_results"))
                    if isinstance(data, dict)
                    else True
                )
                page = arguments["page"]
                per_page = arguments["per_page"]
                returned = len(items)
                accessible_total = min(total, 1000) if total_is_integer else None
                consumed = (page - 1) * per_page + returned
                has_more = bool(
                    returned
                    and accessible_total is not None
                    and consumed < accessible_total
                )
                retrieval_capped = bool(total_is_integer and total > 1000)
                result["metadata"] = {
                    "returned": returned,
                    "total_results": total if total_is_integer else None,
                    "total_results_is_exact": bool(total_is_integer and not incomplete),
                    "upstream_incomplete_results": incomplete,
                    "accessible_results": accessible_total,
                    "retrieval_cap": 1000,
                    "retrieval_capped": retrieval_capped,
                    "page": page,
                    "per_page": per_page,
                    "has_more": has_more,
                    "next_page": page + 1 if has_more else None,
                    "truncated": page > 1 or has_more or retrieval_capped or incomplete,
                    "result_set_complete": bool(
                        total_is_integer
                        and not incomplete
                        and not retrieval_capped
                        and page == 1
                        and returned == total
                    ),
                    "pagination_scope": "github_search_first_1000_results",
                    "warning": (
                        f"GitHub reports {total} matches but exposes only the first 1000 search results. Narrow the query to retrieve records beyond that window."
                        if retrieval_capped
                        else (
                            "GitHub marked this search response incomplete; total_count may be unreliable."
                            if incomplete
                            else None
                        )
                    ),
                }

            if (
                self.tool_config.get("fields", {}).get("pagination")
                == "usgs_offset_count"
            ):
                data = result.get("data")
                features = data.get("features", []) if isinstance(data, dict) else []
                if not isinstance(features, list):
                    features = []
                returned = len(features)
                offset = arguments["offset"]
                limit = arguments["limit"]
                total_is_exact = isinstance(usgs_total, int) and not isinstance(
                    usgs_total, bool
                )
                if total_is_exact:
                    has_more = bool(returned and offset - 1 + returned < usgs_total)
                    stalled = bool(not returned and offset <= usgs_total)
                    matches_lower_bound = usgs_total
                else:
                    has_more = returned == limit
                    stalled = False
                    matches_lower_bound = offset - 1 + returned + (1 if has_more else 0)
                result["metadata"] = {
                    "returned": returned,
                    "total_results": usgs_total if total_is_exact else None,
                    "total_results_is_exact": total_is_exact,
                    "matches_lower_bound": matches_lower_bound,
                    "offset": offset,
                    "offset_base": 1,
                    "limit": limit,
                    "orderby": arguments.get("orderby"),
                    "has_more": has_more,
                    "next_offset": offset + returned if has_more else None,
                    "truncated": offset > 1 or has_more,
                    "result_set_complete": bool(
                        total_is_exact and offset == 1 and returned == usgs_total
                    ),
                    "pagination_stalled": stalled,
                    "pagination_scope": "usgs_fdsn_offset_with_count_endpoint",
                    "count_endpoint_error": usgs_count_error,
                    "warning": (
                        "USGS count endpoint was unavailable; total_results is unknown and has_more is inferred from a full page."
                        if not total_is_exact
                        else (
                            "USGS reported additional events but returned no records at this offset."
                            if stalled
                            else None
                        )
                    ),
                }

            if (
                self.tool_config.get("fields", {}).get("pagination")
                == "nws_client_offset"
            ):
                data = result.get("data")
                features = data.get("features", []) if isinstance(data, dict) else []
                if not isinstance(features, list):
                    features = []
                total = len(features)
                offset = arguments["offset"]
                limit = arguments["limit"]
                page = features[offset : offset + limit]
                returned = len(page)
                has_more = offset + returned < total
                if isinstance(data, dict):
                    data["features"] = page
                result["count"] = returned
                result["metadata"] = {
                    "returned": returned,
                    "total_results": total,
                    "total_results_is_exact": True,
                    "offset": offset,
                    "limit": limit,
                    "has_more": has_more,
                    "next_offset": offset + returned if returned and has_more else None,
                    "truncated": offset > 0 or has_more,
                    "result_set_complete": offset == 0 and returned == total,
                    "pagination_scope": "client_page_complete_nws_active_alert_set",
                    "upstream_limit_supported": False,
                }

            if self.tool_config.get("fields", {}).get("pagination") == "jpl_cad_offset":
                data = result.get("data")
                records = data.get("data", []) if isinstance(data, dict) else []
                if not isinstance(records, list):
                    records = []
                returned = len(records)
                total = data.get("total") if isinstance(data, dict) else None
                total_is_exact = isinstance(total, int) and not isinstance(total, bool)
                offset = arguments["offset"]
                limit = arguments["limit"]
                has_more = bool(
                    total_is_exact and returned and offset + returned < total
                )
                stalled = bool(total_is_exact and not returned and offset < total)
                result["metadata"] = {
                    "returned": returned,
                    "total_results": total if total_is_exact else None,
                    "total_results_is_exact": total_is_exact,
                    "offset": offset,
                    "limit": limit,
                    "sort": arguments.get("sort"),
                    "has_more": has_more,
                    "next_offset": offset + returned if has_more else None,
                    "truncated": offset > 0 or has_more,
                    "result_set_complete": bool(
                        total_is_exact and offset == 0 and returned == total
                    ),
                    "pagination_stalled": stalled,
                    "pagination_scope": "jpl_cad_limit_from",
                    "warning": (
                        "JPL CAD reported additional approaches but returned no records at this offset."
                        if stalled
                        else None
                    ),
                }

            if (
                self.tool_config.get("fields", {}).get("pagination")
                == "wikidata_continue"
            ):
                data = result.get("data")
                records = data.get("search", []) if isinstance(data, dict) else []
                if not isinstance(records, list):
                    records = []
                returned = len(records)
                cursor = arguments["continue"]
                next_cursor = (
                    data.get("search-continue") if isinstance(data, dict) else None
                )
                has_more = isinstance(next_cursor, int) and not isinstance(
                    next_cursor, bool
                )
                final_position_known = not has_more
                result["metadata"] = {
                    "returned": returned,
                    "continue": cursor,
                    "limit": arguments["limit"],
                    "has_more": has_more,
                    "next_continue": next_cursor if has_more else None,
                    "total_results": cursor + returned
                    if final_position_known
                    else None,
                    "total_results_is_exact": final_position_known,
                    "matches_lower_bound": cursor + returned + (1 if has_more else 0),
                    "truncated": cursor > 0 or has_more,
                    "result_set_complete": cursor == 0 and not has_more,
                    "pagination_scope": "wikidata_search_continue_cursor",
                }

            if self.tool_config.get("fields", {}).get("pagination") == "ror_page":
                data = result.get("data")
                errors = data.get("errors") if isinstance(data, dict) else None
                if errors:
                    return {
                        "status": "error",
                        "error": f"{self.api_name}: ROR rejected the query",
                        "detail": errors,
                        "url": url,
                    }
                records = data.get("items", []) if isinstance(data, dict) else []
                if not isinstance(records, list):
                    records = []
                returned = len(records)
                total = (
                    data.get("number_of_results") if isinstance(data, dict) else None
                )
                total_is_exact = isinstance(total, int) and not isinstance(total, bool)
                page = arguments["page"]
                page_size = 20
                consumed = (page - 1) * page_size + returned
                has_more = bool(total_is_exact and returned and consumed < total)
                result["metadata"] = {
                    "returned": returned,
                    "total_results": total if total_is_exact else None,
                    "total_results_is_exact": total_is_exact,
                    "page": page,
                    "page_size": page_size,
                    "page_size_fixed_by_upstream": True,
                    "has_more": has_more,
                    "next_page": page + 1 if has_more else None,
                    "truncated": page > 1 or has_more,
                    "result_set_complete": bool(
                        total_is_exact and page == 1 and returned == total
                    ),
                    "pagination_scope": "ror_v2_fixed_20_record_pages",
                }

            if self.tool_config.get("fields", {}).get("pagination") == "nci_r4r_from":
                data = result.get("data")
                meta = data.get("meta", {}) if isinstance(data, dict) else {}
                records = data.get("results", []) if isinstance(data, dict) else []
                if not isinstance(records, list):
                    records = []
                returned = len(records)
                total = meta.get("totalResults") if isinstance(meta, dict) else None
                total_is_exact = isinstance(total, int) and not isinstance(total, bool)
                start = meta.get("from", arguments["from"])
                if isinstance(start, bool) or not isinstance(start, int):
                    start = arguments["from"]
                has_more = bool(
                    total_is_exact and returned and start + returned < total
                )
                stalled = bool(total_is_exact and not returned and start < total)
                result["metadata"] = {
                    "returned": returned,
                    "total_results": total if total_is_exact else None,
                    "total_results_is_exact": total_is_exact,
                    "from": start,
                    "size": arguments["size"],
                    "has_more": has_more,
                    "next_from": start + returned if has_more else None,
                    "truncated": start > 0 or has_more,
                    "result_set_complete": bool(
                        total_is_exact and start == 0 and returned == total
                    ),
                    "pagination_stalled": stalled,
                    "pagination_scope": "nci_r4r_from_total_results",
                    "warning": (
                        "NCI R4R reported additional resources but returned no records at this offset."
                        if stalled
                        else None
                    ),
                }

            if self.tool_config.get("fields", {}).get("pagination") == "ncbi_esearch":
                data = result.get("data")
                esearch = (
                    data.get("esearchresult", {}) if isinstance(data, dict) else {}
                )
                ids = esearch.get("idlist", []) if isinstance(esearch, dict) else []
                if not isinstance(ids, list):
                    ids = []

                def parse_nonnegative_integer(value: Any) -> Optional[int]:
                    try:
                        parsed = int(value)
                    except (TypeError, ValueError):
                        return None
                    return parsed if parsed >= 0 else None

                total = parse_nonnegative_integer(esearch.get("count"))
                start = parse_nonnegative_integer(esearch.get("retstart"))
                if start is None:
                    start = arguments["retstart"]
                returned = len(ids)
                has_more = bool(
                    total is not None and returned and start + returned < total
                )
                stalled = bool(total is not None and not returned and start < total)
                result["metadata"] = {
                    "returned": returned,
                    "total_results": total,
                    "total_results_is_exact": total is not None,
                    "retstart": start,
                    "retmax": arguments["retmax"],
                    "has_more": has_more,
                    "next_retstart": start + returned if has_more else None,
                    "truncated": start > 0 or has_more,
                    "result_set_complete": bool(
                        total is not None and start == 0 and returned == total
                    ),
                    "pagination_stalled": stalled,
                    "pagination_scope": "ncbi_esearch_retstart_count",
                    "warning": (
                        "NCBI ESearch reported additional IDs but returned an empty page at this retstart."
                        if stalled
                        else None
                    ),
                }

            if self.tool_config.get("fields", {}).get("pagination") == "openfda_skip":
                data = result.get("data") or {}
                count_mode = bool(arguments.get("count"))
                records = data.get("results", []) if isinstance(data, dict) else []
                returned = len(records) if isinstance(records, list) else 0
                if count_mode:
                    limit = arguments.get("limit", 1)
                    terms_truncated = returned >= limit
                    result["metadata"] = {
                        "mode": "count_aggregation",
                        "count_field": arguments.get("count"),
                        "returned_terms": returned,
                        "term_limit": limit,
                        "total_terms": None,
                        "total_terms_is_exact": False,
                        "has_more": False,
                        "next_skip": None,
                        "upstream_truncated": terms_truncated,
                        "warning": (
                            "openFDA count mode does not support skip. The term list reached "
                            "the requested limit; increase limit up to 1000 or refine the search."
                            if terms_truncated
                            else None
                        ),
                    }
                    return result
                api_meta = (
                    data.get("meta", {}).get("results", {})
                    if isinstance(data, dict)
                    else {}
                )
                total = api_meta.get("total")
                total_is_exact = isinstance(total, int) and not isinstance(total, bool)
                skip = api_meta.get("skip", arguments.get("skip", 0))
                limit = api_meta.get("limit", arguments.get("limit", 1))
                # openFDA permits skip <= 25,000 and limit <= 100, so at most
                # the first 25,100 ranked records of a broad query are reachable.
                accessible = min(total, 25100) if total_is_exact else None
                upstream_truncated = total_is_exact and total > 25100
                has_more = bool(
                    returned and accessible is not None and skip + returned < accessible
                )
                result["metadata"] = {
                    "returned": returned,
                    "total_results": total if total_is_exact else None,
                    "total_results_is_exact": total_is_exact,
                    "accessible_results": accessible,
                    "upstream_truncated": upstream_truncated,
                    "skip": skip,
                    "limit": limit,
                    "has_more": has_more,
                    "next_skip": skip + returned if has_more else None,
                    "truncated": has_more or upstream_truncated,
                    "result_set_complete": bool(
                        total_is_exact and skip == 0 and returned == total
                    ),
                    "warning": (
                        "openFDA matched more than 25,100 records, but its API allows "
                        "skip only through 25,000 with at most 100 records per call. "
                        "Refine the search to reach records outside this ranked window."
                        if upstream_truncated
                        else None
                    ),
                }

            if (
                self.tool_config.get("fields", {}).get("pagination")
                == "drf_limit_offset"
            ):
                data = result.get("data") or {}
                records = data.get("results", []) if isinstance(data, dict) else []
                if not isinstance(records, list):
                    records = []
                returned = len(records)
                total = data.get("count") if isinstance(data, dict) else None
                total_is_exact = isinstance(total, int) and not isinstance(total, bool)
                offset = arguments["offset"]
                limit = arguments["limit"]
                next_url = data.get("next") if isinstance(data, dict) else None
                previous_url = data.get("previous") if isinstance(data, dict) else None
                has_more = bool(next_url) or bool(
                    total_is_exact and returned and offset + returned < total
                )
                next_offset = offset + returned if has_more else None
                if next_url:
                    try:
                        query = urllib.parse.parse_qs(
                            urllib.parse.urlparse(next_url).query
                        )
                        if query.get("offset"):
                            next_offset = int(query["offset"][0])
                    except (TypeError, ValueError):
                        pass
                stalled = bool(total_is_exact and not returned and offset < total)
                result["count"] = returned
                result["metadata"] = {
                    "returned": returned,
                    "total_results": total if total_is_exact else None,
                    "total_results_is_exact": total_is_exact,
                    "offset": offset,
                    "limit": limit,
                    "has_more": has_more,
                    "next_offset": next_offset,
                    "next_url": next_url,
                    "previous_url": previous_url,
                    "truncated": offset > 0 or has_more,
                    "result_set_complete": bool(
                        total_is_exact and offset == 0 and returned == total
                    ),
                    "pagination_stalled": stalled,
                    "pagination_scope": "django_rest_framework_count_limit_offset",
                    "warning": (
                        "The API reported additional records but returned an empty page at this offset."
                        if stalled
                        else None
                    ),
                }

            if self.tool_config.get("fields", {}).get("pagination") == "biorxiv_cursor":
                data = result.get("data") or {}
                records = data.get("collection", []) if isinstance(data, dict) else []
                if not isinstance(records, list):
                    records = []
                messages = data.get("messages", []) if isinstance(data, dict) else []
                message = messages[0] if isinstance(messages, list) and messages else {}

                def numeric(value):
                    try:
                        return int(value)
                    except (TypeError, ValueError):
                        return None

                returned = len(records)
                cursor = arguments["cursor"]
                total = (
                    numeric(message.get("total")) if isinstance(message, dict) else None
                )
                new_papers = (
                    numeric(message.get("count_new_papers"))
                    if isinstance(message, dict)
                    else None
                )
                total_is_exact = total is not None and total >= 0
                has_more = bool(
                    total_is_exact and returned and cursor + returned < total
                )
                stalled = bool(total_is_exact and not returned and cursor < total)
                result["count"] = returned
                result["metadata"] = {
                    "returned": returned,
                    "upstream_reported_page_count": (
                        numeric(message.get("count"))
                        if isinstance(message, dict)
                        else None
                    ),
                    "total_results": total if total_is_exact else None,
                    "total_results_is_exact": total_is_exact,
                    "unique_new_papers": new_papers,
                    "unique_new_papers_is_exact": new_papers is not None,
                    "cursor": cursor,
                    "cursor_semantics": "zero_based_record_offset_not_page_number",
                    "has_more": has_more,
                    "next_cursor": cursor + returned if has_more else None,
                    "truncated": cursor > 0 or has_more,
                    "result_set_complete": bool(
                        total_is_exact and cursor == 0 and returned == total
                    ),
                    "pagination_stalled": stalled,
                    "pagination_scope": "biorxiv_details_total_offset_batches",
                    "warning": (
                        "bioRxiv reported additional records but returned an empty batch at this cursor."
                        if stalled
                        else None
                    ),
                }

            if (
                self.tool_config.get("fields", {}).get("pagination")
                == "marine_regions_offset"
            ):
                records = result.get("data")
                if not isinstance(records, list):
                    return {
                        "status": "error",
                        "error": "Marine Regions returned a non-array search response",
                        "url": url,
                    }
                returned = len(records)
                offset = arguments["offset"]
                page_size = 100
                has_more = False
                probe_error = None
                if returned == page_size:
                    try:
                        probe_params = dict(params)
                        probe_params["offset"] = offset + returned
                        probe_params["count"] = 1
                        probe = request_with_retry(
                            self.session,
                            "GET",
                            url,
                            params=probe_params,
                            headers=custom_headers,
                            timeout=self.timeout,
                            max_attempts=3,
                        )
                        probe_data = probe.json() if probe.status_code == 200 else None
                        if not isinstance(probe_data, list):
                            raise ValueError(
                                f"lookahead returned HTTP {probe.status_code} or non-array data"
                            )
                        has_more = bool(probe_data)
                    except (ValueError, requests.RequestException) as exc:
                        has_more = None
                        probe_error = str(exc)
                terminal = has_more is False
                total = offset + returned if terminal else None
                result["count"] = returned
                result["metadata"] = {
                    "returned": returned,
                    "offset": offset,
                    "page_size": page_size,
                    "total_results": total,
                    "total_results_is_exact": terminal,
                    "matches_lower_bound": (
                        offset + returned + 1 if has_more else offset + returned
                    ),
                    "has_more": has_more,
                    "next_offset": offset + returned if has_more else None,
                    "truncated": offset > 0 or has_more is not False,
                    "result_set_complete": bool(offset == 0 and terminal),
                    "lookahead_used": returned == page_size,
                    "pagination_scope": "marine_regions_query_offset_count_100",
                    "warning": (
                        f"Could not verify whether another page exists: {probe_error}"
                        if probe_error
                        else None
                    ),
                }

            # DBLP search endpoints expose two different quantities:
            # @total is every theoretical match, while @computed is the ranked
            # window the search engine made accessible. Use @computed for
            # continuation so agents are never directed to an unreachable deep
            # page, but retain @total and warn when the upstream window truncates.
            if self.tool_config.get("fields", {}).get("pagination") == "dblp_offset":
                data = result.get("data", {})
                hits_data = (
                    data.get("result", {}).get("hits", {})
                    if isinstance(data, dict)
                    else {}
                )
                hits = hits_data.get("hit", []) if isinstance(hits_data, dict) else []
                if isinstance(hits, dict):
                    returned = 1
                elif isinstance(hits, list):
                    returned = len(hits)
                else:
                    returned = 0

                def _int_metadata(key, default):
                    try:
                        return int(hits_data.get(key, default))
                    except (TypeError, ValueError):
                        return default

                requested_offset = arguments.get("offset", 0)
                total = _int_metadata("@total", returned)
                accessible = _int_metadata("@computed", total)
                first = _int_metadata("@first", requested_offset)
                has_more = first + returned < accessible
                result["metadata"] = {
                    "total_matches": total,
                    "accessible_results": accessible,
                    "upstream_truncated": accessible < total,
                    "returned": returned,
                    "offset": first,
                    "requested_offset": requested_offset,
                    "limit": arguments.get("limit", 10),
                    "has_more": has_more,
                    "next_offset": (
                        first + returned if returned and has_more else None
                    ),
                    "truncated": has_more or accessible < total,
                    "warning": (
                        "DBLP matched more records than its search engine computed "
                        "for this query. Pagination can traverse only "
                        "accessible_results; refine the query to reach records "
                        "outside that ranked window."
                        if accessible < total
                        else None
                    ),
                }

            # Client-side limit for APIs that return unbounded lists
            if self.tool_config.get("fields", {}).get("client_side_limit"):
                props = self.tool_config.get("parameter", {}).get("properties", {})
                limit = arguments.get("limit", props.get("limit", {}).get("default"))
                data = result.get("data")
                if isinstance(data, list):
                    preserve_header = self.tool_config.get("fields", {}).get(
                        "client_side_limit_preserve_header"
                    )
                    if preserve_header:
                        # Tabular APIs such as Census return a 2D array whose
                        # first row is the schema/header.  Counts and caller
                        # limits refer to records, not that mandatory header.
                        total_records = max(0, len(data) - 1)
                        result["count"] = total_records
                        if limit is not None:
                            max_items = max(0, int(limit))
                            if total_records > max_items:
                                result["total_before_limit"] = total_records
                                result["data"] = data[: max_items + 1]
                            result["count"] = min(total_records, max_items)
                    elif limit is not None and len(data) > max(0, int(limit)):
                        max_items = max(0, int(limit))
                        result["total_before_limit"] = len(data)
                        result["data"] = data[:max_items]
                        result["count"] = max_items

            # Disclose server-side pagination/truncation at the top level for
            # tools that opt in via `fields.pagination_disclosure`.
            self._apply_pagination_disclosure(result)

            # Fix-R32C-4/5: an exact-match backend (e.g. CPIC's PostgREST
            # name=eq.{name}) silently returns status:success with an empty
            # list for any name that isn't spelled/named exactly as the
            # database stores it -- confirmed live for well-known aliases
            # ("FK506" for tacrolimus) and spelling variants ("cyclosporin"
            # vs the indexed "cyclosporine"), indistinguishable from "no PGx
            # data exists for this drug". `fields.empty_result_note` lets a
            # config surface the real constraint instead of a bare empty list.
            empty_note = self.tool_config.get("fields", {}).get("empty_result_note")
            if (
                empty_note
                and isinstance(result.get("data"), list)
                and not result["data"]
            ):
                result["note"] = empty_note

            return result

        except Exception as e:
            return {
                "status": "error",
                "error": redact_url_secrets(f"{self.api_name} API error: {str(e)}"),
                "url": url,
            }
