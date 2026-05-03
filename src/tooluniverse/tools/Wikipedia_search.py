"""
Wikipedia_search

Search Wikipedia articles using MediaWiki API. Returns a list of matching articles with titles, s...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Wikipedia_search(
    query: str,
    limit: Optional[int] = 10,
    language: Optional[str] = "en",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search Wikipedia articles using MediaWiki API. Returns a list of matching articles with titles, s...

    Parameters
    ----------
    query : str
        Search query string to find Wikipedia articles
    limit : int
        Maximum number of results to return (default: 10, max: 50)
    language : str
        Wikipedia language code (e.g., 'en' for English, 'zh' for Chinese, 'fr' for F...
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
        for k, v in {"query": query, "limit": limit, "language": language}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Wikipedia_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Wikipedia_search"]
