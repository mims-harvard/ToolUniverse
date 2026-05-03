"""
Web search tools for ToolUniverse using DDGS (Dux Distributed Global Search).

This module provides web search capabilities using the ddgs library,
which supports multiple search engines including DuckDuckGo, Google, Bing, etc.
"""

import json
import re
import subprocess
import sys
import time
from html import unescape
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, unquote, urlparse

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("WebSearchTool")
class WebSearchTool(BaseTool):
    """
    Web search tool using DDGS library.

    This tool performs web searches using the DDGS library which supports
    multiple search engines including Google, Bing, Brave, Yahoo, DuckDuckGo, etc.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        # DDGS instance will be created per request to avoid session issues

    def _search_with_ddgs(
        self,
        query: str,
        max_results: int = 10,
        backend: str = "auto",
        region: str = "us-en",
        safesearch: str = "moderate",
    ) -> List[Dict[str, Any]]:
        """
        Perform a web search using DDGS library and return formatted results.

        Args:
            query: Search query string
            max_results: Maximum number of results to return
            backend: Search engine backend (auto, google, bing, brave, etc.)
            region: Search region (e.g., 'us-en', 'cn-zh')
            safesearch: Safe search level ('on', 'moderate', 'off')

        Returns:
            List of search results with title, url, and snippet
        """
        # Run DDGS in a subprocess so native-library panics cannot crash the
        # current ToolUniverse process.
        payload = {
            "query": query,
            "max_results": max_results,
            "backend": backend,
            "region": region,
            "safesearch": safesearch,
        }
        ddgs_script = """
import json
import sys
from ddgs import DDGS

args = json.loads(sys.argv[1])
results = list(
    DDGS().text(
        query=args["query"],
        max_results=args["max_results"],
        backend=args["backend"],
        region=args["region"],
        safesearch=args["safesearch"],
    )
)
print(json.dumps(results))
"""

        completed = subprocess.run(
            [sys.executable, "-c", ddgs_script, json.dumps(payload)],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if completed.returncode != 0:
            stderr_preview = (completed.stderr or "").strip()[:300]
            stdout_preview = (completed.stdout or "").strip()[:300]
            detail = stderr_preview or stdout_preview or "Unknown subprocess failure"
            raise RuntimeError(
                f"DDGS subprocess failed with exit code {completed.returncode}: {detail}"
            )

        try:
            search_results = json.loads(completed.stdout or "[]")
        except json.JSONDecodeError as error:
            raise RuntimeError(
                f"DDGS subprocess returned invalid JSON: {str(error)}"
            ) from error

        # Convert DDGS results to our expected format
        results = []
        for i, result in enumerate(search_results):
            results.append(
                {
                    "title": result.get("title", ""),
                    "url": result.get("href", ""),
                    "snippet": result.get("body", ""),
                    "rank": i + 1,
                }
            )

        return results

    def _search_with_fallback(
        self,
        query: str,
        max_results: int,
        backend: str,
        region: str,
        safesearch: str,
    ) -> Tuple[
        List[Dict[str, Any]],
        Optional[str],
        List[str],
        Optional[str],
        Dict[str, str],
    ]:
        """
        Search with backend fallback strategy.

        Returns:
            (results, backend_used, attempted_backends, warning, provider_errors)
        """
        attempted_backends = []
        last_error = None
        provider_errors: Dict[str, str] = {}
        had_empty_success = False
        backends_to_try = [backend]
        stop_ddgs_backends = False

        if backend == "auto":
            # Try the explicit DuckDuckGo backend first. It tends to fail with
            # regular Python exceptions in restricted environments, while some
            # other backends can trigger native panics.
            backends_to_try = ["duckduckgo", "auto", "bing", "brave"]
        else:
            backends_to_try.append("auto")

        seen = set()
        unique_backends = []
        for backend_name in backends_to_try:
            if backend_name not in seen:
                seen.add(backend_name)
                unique_backends.append(backend_name)

        for backend_name in unique_backends:
            if stop_ddgs_backends:
                break

            attempted_backends.append(backend_name)
            try:
                results = self._search_with_ddgs(
                    query=query,
                    max_results=max_results,
                    backend=backend_name,
                    region=region,
                    safesearch=safesearch,
                )
                if results:
                    return (
                        results,
                        backend_name,
                        attempted_backends,
                        None,
                        provider_errors,
                    )
                had_empty_success = True
            except Exception as error:
                error_str = str(error)
                last_error = error_str
                provider_errors[backend_name] = error_str
                # If DNS resolution is unavailable, additional DDGS backends
                # are unlikely to help and may trigger avoidable native panics.
                if any(
                    token in error_str
                    for token in [
                        "NameResolutionError",
                        "nodename nor servname provided",
                        "Temporary failure in name resolution",
                    ]
                ):
                    stop_ddgs_backends = True
                continue

        # Fallback providers that do not depend on DDGS.
        provider_chain = [
            ("duckduckgo_html", self._search_with_duckduckgo_html),
            ("wikipedia_api", self._search_with_wikipedia_api),
        ]

        for provider_name, provider_func in provider_chain:
            attempted_backends.append(provider_name)
            try:
                results = provider_func(query=query, max_results=max_results)
                if results:
                    return (
                        results,
                        provider_name,
                        attempted_backends,
                        None,
                        provider_errors,
                    )
                had_empty_success = True
            except Exception as error:
                last_error = str(error)
                provider_errors[provider_name] = str(error)
                continue

        # Return clean empty set + last error context when every provider fails
        # or no provider had results.
        if had_empty_success:
            return [], "empty", attempted_backends, None, provider_errors

        warning = (
            "All search providers failed"
            if provider_errors
            else (last_error or "No search providers returned results")
        )
        return [], "none", attempted_backends, warning, provider_errors

    def _search_with_duckduckgo_html(
        self, query: str, max_results: int
    ) -> List[Dict[str, Any]]:
        """Fallback provider: parse DuckDuckGo HTML results without DDGS."""
        response = requests.get(
            "https://duckduckgo.com/html/",
            params={"q": query},
            timeout=15,
            headers={"User-Agent": "ToolUniverse/1.0"},
        )
        response.raise_for_status()
        html_text = response.text

        result_pattern = re.compile(
            r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
            flags=re.IGNORECASE | re.DOTALL,
        )
        snippet_pattern = re.compile(
            r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
            flags=re.IGNORECASE | re.DOTALL,
        )

        anchors = result_pattern.findall(html_text)
        snippets = snippet_pattern.findall(html_text)
        results = []

        for index, (href, raw_title) in enumerate(anchors[:max_results], start=1):
            parsed_href = href
            if href.startswith("/l/?") or "uddg=" in href:
                parsed = urlparse(href)
                query_map = parse_qs(parsed.query)
                uddg_values = query_map.get("uddg")
                if uddg_values:
                    parsed_href = unquote(uddg_values[0])

            clean_title = unescape(re.sub(r"<[^>]+>", "", raw_title)).strip()
            raw_snippet = snippets[index - 1] if index - 1 < len(snippets) else ""
            clean_snippet = unescape(re.sub(r"<[^>]+>", "", raw_snippet)).strip()

            if not parsed_href:
                continue

            results.append(
                {
                    "title": clean_title,
                    "url": parsed_href,
                    "snippet": clean_snippet,
                    "rank": index,
                }
            )

        return results

    def _search_with_wikipedia_api(
        self, query: str, max_results: int
    ) -> List[Dict[str, Any]]:
        """Fallback provider: Wikipedia OpenSearch API."""
        response = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "opensearch",
                "search": query,
                "limit": max_results,
                "namespace": 0,
                "format": "json",
            },
            timeout=15,
            headers={"User-Agent": "ToolUniverse/1.0"},
        )
        response.raise_for_status()
        data = response.json()

        if not isinstance(data, list) or len(data) < 4:
            return []

        titles = data[1] if isinstance(data[1], list) else []
        descriptions = data[2] if isinstance(data[2], list) else []
        urls = data[3] if isinstance(data[3], list) else []

        results = []
        for index, title in enumerate(titles[:max_results], start=1):
            url = urls[index - 1] if index - 1 < len(urls) else ""
            snippet = descriptions[index - 1] if index - 1 < len(descriptions) else ""
            if not url:
                continue
            results.append(
                {
                    "title": str(title),
                    "url": str(url),
                    "snippet": str(snippet),
                    "rank": index,
                }
            )
        return results

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute web search using DDGS.

        Args:
            arguments: Dictionary containing:
                - query: Search query string
                - max_results: Maximum number of results (default: 10)
                - search_type: Type of search (default: 'general')
                - backend: Search engine backend (default: 'auto')
                - region: Search region (default: 'us-en')
                - safesearch: Safe search level (default: 'moderate')

        Returns:
            Dictionary containing search results
        """
        try:
            query = arguments.get("query", "").strip()
            max_results = int(arguments.get("max_results", 10))
            search_type = arguments.get("search_type", "general")
            backend = arguments.get("backend", "auto")
            region = arguments.get("region", "us-en")
            safesearch = arguments.get("safesearch", "moderate")

            if not query:
                error_msg = "Query parameter is required"
                return {
                    "status": "error",
                    "error": error_msg,
                    "data": {
                        "status": "error",
                        "error": error_msg,
                        "query": "",
                        "total_results": 0,
                        "results": [],
                    },
                }

            # Validate max_results
            max_results = max(1, min(max_results, 50))  # Limit between 1-50

            # Modify query based on search type
            if search_type == "api_documentation":
                query = f"{query} API documentation python library"
            elif search_type == "python_packages":
                query = f"{query} python package pypi"
            elif search_type == "github":
                query = f"{query} site:github.com"

            # Perform search using fallback backends to improve reliability.
            (
                results,
                backend_used,
                attempted_backends,
                search_warning,
                provider_errors,
            ) = self._search_with_fallback(
                query=query,
                max_results=max_results,
                backend=backend,
                region=region,
                safesearch=safesearch,
            )

            if search_warning:
                return {
                    "status": "success",
                    "warning": search_warning,
                    "data": {
                        "status": "success",
                        "query": query,
                        "search_type": search_type,
                        "total_results": 0,
                        "results": [],
                        "attempted_backends": attempted_backends,
                        "backend_used": backend_used or "none",
                        "all_providers_failed": backend_used == "none",
                        "provider_errors": provider_errors,
                        "warning": search_warning,
                    },
                }

            # Add rate limiting to be respectful
            time.sleep(0.5)

            result_data = {
                "status": "success",
                "query": query,
                "search_type": search_type,
                "total_results": len(results),
                "results": results,
                "backend_used": backend_used or backend,
                "attempted_backends": attempted_backends,
            }
            if provider_errors:
                result_data["provider_errors"] = provider_errors

            return {"status": "success", "data": result_data}

        except Exception as e:
            error_msg = str(e)
            return {
                "status": "error",
                "error": error_msg,
                "data": {
                    "status": "error",
                    "error": error_msg,
                    "query": arguments.get("query", ""),
                    "total_results": 0,
                    "results": [],
                },
            }


@register_tool("WebAPIDocumentationSearchTool")
class WebAPIDocumentationSearchTool(WebSearchTool):
    """
    Specialized web search tool for API documentation and Python libraries.

    This tool is optimized for finding API documentation, Python packages,
    and technical resources using DDGS with multiple search engines.
    """

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute API documentation focused search.

        Args:
            arguments: Dictionary containing:
                - query: Search query string
                - max_results: Maximum number of results (default: 10)
                - focus: Focus area ('api_docs', 'python_packages', etc.)
                - backend: Search engine backend (default: 'auto')

        Returns:
            Dictionary containing search results
        """
        try:
            query = arguments.get("query", "").strip()
            focus = arguments.get("focus", "api_docs")
            backend = arguments.get("backend", "auto")

            if not query:
                error_msg = "Query parameter is required"
                return {
                    "status": "error",
                    "error": error_msg,
                    "data": {
                        "status": "error",
                        "error": error_msg,
                        "query": "",
                        "total_results": 0,
                        "results": [],
                    },
                }

            # Modify query based on focus
            if focus == "api_docs":
                enhanced_query = f'"{query}" API documentation official docs'
            elif focus == "python_packages":
                enhanced_query = f'"{query}" python package pypi install pip'
            elif focus == "github_repos":
                enhanced_query = f'"{query}" github repository source code'
            else:
                enhanced_query = f'"{query}" documentation API reference'

            # Use parent class search with enhanced query
            arguments["query"] = enhanced_query
            arguments["search_type"] = "api_documentation"
            arguments["backend"] = backend

            result = super().run(arguments)

            # Extract data from parent result and add focus-specific metadata
            if result["status"] == "success" and "data" in result:
                result_data = result["data"]
                result_data["focus"] = focus
                result_data["enhanced_query"] = enhanced_query

                # Filter results for better relevance
                if focus == "python_packages":
                    result_data["results"] = [
                        r
                        for r in result_data["results"]
                        if (
                            "pypi.org" in r.get("url", "")
                            or "python" in r.get("title", "").lower()
                        )
                    ]
                elif focus == "github_repos":
                    result_data["results"] = [
                        r
                        for r in result_data["results"]
                        if "github.com" in r.get("url", "")
                    ]

                # Update total_results after filtering
                result_data["total_results"] = len(result_data["results"])

                return {"status": "success", "data": result_data}

            return result

        except Exception as e:
            error_msg = str(e)
            return {
                "status": "error",
                "error": error_msg,
                "data": {
                    "status": "error",
                    "error": error_msg,
                    "query": arguments.get("query", ""),
                    "total_results": 0,
                    "results": [],
                },
            }
