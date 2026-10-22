"""
NDEx_search_networks

Search the NDEx biological network repository with zero-based page-index pagination and pages up ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NDEx_search_networks(
    query: str,
    size: Optional[int] = None,
    start: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the NDEx biological network repository with zero-based page-index pagination and pages up ...

    Parameters
    ----------
    query : str
        Search query for finding biological networks. Can include gene names, pathway...
    size : int
        Networks per search window (default 10, max 1000).
    start : int
        Zero-based NDEx page index, not a record offset (default 0). Continue with me...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    Any
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {"query": query, "size": size, "start": start}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "NDEx_search_networks",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NDEx_search_networks"]
