"""
MonarchV3_search

Search the Monarch Initiative knowledge graph for biomedical entities by name or keyword. Returns...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MonarchV3_search(
    query: Optional[str] = None,
    limit: Optional[int] = None,
    category: Optional[str] = None,
    q: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search the Monarch Initiative knowledge graph for biomedical entities by name or keyword. Returns...

    Parameters
    ----------
    query : str
        Search query. Can be gene names, disease names, phenotype terms, etc. Example...
    limit : int
        Maximum results to return (default: 10, max: 50).
    category : str
        Filter by entity category. Options: 'biolink:Gene', 'biolink:Disease', 'bioli...
    q : str
        Alias for query parameter.
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
            "limit": limit,
            "category": category,
            "q": q,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MonarchV3_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MonarchV3_search"]
