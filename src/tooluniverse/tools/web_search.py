"""
web_search

General web search using DDGS (Dux Distributed Global Search) supporting multiple search engines ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def web_search(
    query: str,
    max_results: Optional[int] = 10,
    search_type: Optional[str] = "general",
    backend: Optional[str] = "auto",
    region: Optional[str] = "us-en",
    safesearch: Optional[str] = "moderate",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    General web search using DDGS (Dux Distributed Global Search) supporting multiple search engines ...

    Parameters
    ----------
    query : str
        Search query string
    max_results : int
        Maximum number of results to return
    search_type : str
        Type of search to perform
    backend : str
        Search engine backend to use
    region : str
        Search region/locale
    safesearch : str
        Safe search level
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
            "search_type": search_type,
            "backend": backend,
            "region": region,
            "safesearch": safesearch,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "web_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["web_search"]
