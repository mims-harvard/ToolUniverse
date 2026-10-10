"""
StatPearls_search

Full-text search of StatPearls, the peer-reviewed point-of-care clinical review library on NCBI B...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def StatPearls_search(
    query: str,
    limit: Optional[int] = 5,
    include_archived: Optional[bool] = False,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Full-text search of StatPearls, the peer-reviewed point-of-care clinical review library on NCBI B...

    Parameters
    ----------
    query : str
        Keywords: a drug, disease or clinical topic plus what you need, e.g. 'amitrip...
    limit : int
        Number of chapters to return (1-10, default 5).
    include_archived : bool
        Also search the archived StatPearls chapters, which the publisher no longer m...
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
        for k, v in {
            "query": query,
            "limit": limit,
            "include_archived": include_archived,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "StatPearls_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["StatPearls_search"]
