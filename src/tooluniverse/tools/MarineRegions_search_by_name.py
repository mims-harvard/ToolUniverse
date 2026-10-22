"""
MarineRegions_search_by_name

Search the Marine Regions Gazetteer (VLIZ) for ocean/sea geographic features by name. Returns at ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MarineRegions_search_by_name(
    name: str,
    like: Optional[bool] = True,
    fuzzy: Optional[bool] = False,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the Marine Regions Gazetteer (VLIZ) for ocean/sea geographic features by name. Returns at ...

    Parameters
    ----------
    name : str
        Name of the marine geographic feature. Examples: 'North Sea', 'Pacific Ocean'...
    like : bool
        If true, perform a partial name match (SQL LIKE). Default: true
    fuzzy : bool
        If true, perform Levenshtein fuzzy matching. Default: false
    offset : int
        Zero-based record offset. Start at 0 and continue with metadata.next_offset.
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
            "like": like,
            "fuzzy": fuzzy,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MarineRegions_search_by_name",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MarineRegions_search_by_name"]
