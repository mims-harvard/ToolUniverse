"""
Monarch_search

Search the Monarch knowledge graph for biomedical entities with exact offset pagination. Metadata...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Monarch_search(
    query: str,
    category: Optional[str] = None,
    limit: Optional[int] = 10,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search the Monarch knowledge graph for biomedical entities with exact offset pagination. Metadata...

    Parameters
    ----------
    query : str
        Search query: gene names, disease names, phenotype terms. Examples: 'BRCA1', ...
    category : str
        Filter by entity category. Options: 'biolink:Gene', 'biolink:Disease', 'bioli...
    limit : int
        Results per page (1-50).
    offset : int
        Zero-based offset. Continue with metadata.next_offset.
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
            "category": category,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Monarch_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Monarch_search"]
