"""
Fatcat_search_scholar

Search Internet Archive Scholar's Fatcat release index and retrieve detailed metadata. Results ar...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Fatcat_search_scholar(
    query: str,
    max_results: Optional[int] = 10,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search Internet Archive Scholar's Fatcat release index and retrieve detailed metadata. Results ar...

    Parameters
    ----------
    query : str
        Search query for Fatcat releases. Use keywords to search across titles, abstr...
    max_results : int
        Number of enriched releases to return per page. Default and maximum are 10; u...
    offset : int
        Zero-based search-result offset. Continue with metadata.next_offset.
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "query": query,
            "max_results": max_results,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Fatcat_search_scholar",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Fatcat_search_scholar"]
