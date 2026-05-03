"""
civic_search_therapies

Search for therapies (drugs/treatments) in CIViC database. Returns a list of cancer therapies and...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def civic_search_therapies(
    limit: Optional[int] = 20,
    name: Optional[str] = None,
    query: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search for therapies (drugs/treatments) in CIViC database. Returns a list of cancer therapies and...

    Parameters
    ----------
    limit : int
        Maximum number of therapies to return (default: 20, recommended max: 100)
    name : str
        Filter by therapy/drug name (e.g., 'imatinib', 'ponatinib', 'pembrolizumab')....
    query : str
        Alias for name. Filter by therapy/drug name.
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
        for k, v in {"limit": limit, "name": name, "query": query}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "civic_search_therapies",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["civic_search_therapies"]
