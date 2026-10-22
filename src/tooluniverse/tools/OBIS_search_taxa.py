"""
OBIS_search_taxa

Resolve an exact scientific name through OBIS /taxon/{scientificname}. Returns same-name accepted...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OBIS_search_taxa(
    scientificname: str,
    size: Optional[int] = 10,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Resolve an exact scientific name through OBIS /taxon/{scientificname}. Returns same-name accepted...

    Parameters
    ----------
    scientificname : str
        Scientific name query (e.g., 'Gadus').
    size : int
        Number of taxon matches to return (1–100).
    offset : int
        Zero-based local offset over exact-name matches. Continue with metadata.next_...
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
            "scientificname": scientificname,
            "size": size,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OBIS_search_taxa",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OBIS_search_taxa"]
