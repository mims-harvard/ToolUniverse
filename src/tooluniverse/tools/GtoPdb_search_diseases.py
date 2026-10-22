"""
GtoPdb_search_diseases

Search the Guide to Pharmacology (GtoPdb / IUPHAR-BPS) for diseases with recoverable local offset...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GtoPdb_search_diseases(
    name: Optional[str] = None,
    query: Optional[str] = None,
    limit: Optional[int] = 50,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the Guide to Pharmacology (GtoPdb / IUPHAR-BPS) for diseases with recoverable local offset...

    Parameters
    ----------
    name : str
        Disease name to search. Examples: 'epilepsy', 'asthma', 'hypertension', 'brea...
    query : str
        Name/keyword to search for. Alias for the "name" parameter.
    limit : int
        Number of diseases on this page (1-1000; default 50).
    offset : int
        Zero-based disease offset. Continue with next_offset while has_more is true.
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
            "name": name,
            "query": query,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GtoPdb_search_diseases",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GtoPdb_search_diseases"]
