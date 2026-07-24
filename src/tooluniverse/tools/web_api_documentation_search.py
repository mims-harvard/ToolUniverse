"""
web_api_documentation_search

Specialized web search for API documentation, Python packages, and technical resources using DDGS...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def web_api_documentation_search(
    query: str,
    max_results: Optional[int] = 10,
    focus: Optional[str] = "api_docs",
    backend: Optional[str] = "auto",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Specialized web search for API documentation, Python packages, and technical resources using DDGS...

    Parameters
    ----------
    query : str
        Search query string (e.g., tool name, library name, API name)
    max_results : int
        Maximum number of results to return
    focus : str
        Focus area for the search
    backend : str
        Search engine backend to use
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "query": query,
            "max_results": max_results,
            "focus": focus,
            "backend": backend,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "web_api_documentation_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["web_api_documentation_search"]
