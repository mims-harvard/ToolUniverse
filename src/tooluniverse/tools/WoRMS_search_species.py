"""
WoRMS_search_species

Search taxon names in the World Register of Marine Species (WoRMS). Exposes the official prefix m...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def WoRMS_search_species(
    query: str,
    limit: Optional[int] = 20,
    offset: Optional[int] = 1,
    like: Optional[bool] = True,
    marine_only: Optional[bool] = True,
    extant_only: Optional[bool] = True,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search taxon names in the World Register of Marine Species (WoRMS). Exposes the official prefix m...

    Parameters
    ----------
    query : str
        Scientific name or name prefix to search.
    limit : int
        Maximum number of taxon records to return (default 20, range 1-1000). Pages l...
    offset : int
        1-based starting record number (default 1). Continue with the returned next_o...
    like : bool
        When true, perform the official prefix/SQL-LIKE search; false requests an exa...
    marine_only : bool
        Limit results to marine taxa. Set false to include non-marine records.
    extant_only : bool
        Limit results to extant taxa. Set false to include extinct records.
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
            "offset": offset,
            "like": like,
            "marine_only": marine_only,
            "extant_only": extant_only,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "WoRMS_search_species",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["WoRMS_search_species"]
