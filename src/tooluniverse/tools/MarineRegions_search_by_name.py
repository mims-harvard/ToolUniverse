"""
MarineRegions_search_by_name

Search the Marine Regions Gazetteer (VLIZ) for ocean/sea geographic features by name. Returns MRG...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MarineRegions_search_by_name(
    name: str,
    like: Optional[bool | Any] = None,
    fuzzy: Optional[bool | Any] = None,
    offset: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the Marine Regions Gazetteer (VLIZ) for ocean/sea geographic features by name. Returns MRG...

    Parameters
    ----------
    name : str
        Name of the marine geographic feature. Examples: 'North Sea', 'Pacific Ocean'...
    like : bool | Any
        If true, perform a partial/fuzzy name match (LIKE search). Default: true
    fuzzy : bool | Any
        If true, perform fuzzy matching for approximate name searches. Default: false
    offset : int | Any
        Pagination offset. Default: 0 (first page)
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

    return get_shared_client().run_one_function(
        {
            "name": "MarineRegions_search_by_name",
            "arguments": {"name": name, "like": like, "fuzzy": fuzzy, "offset": offset},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MarineRegions_search_by_name"]
