"""
OBIS_search_occurrences

Retrieve marine species occurrence records (with coordinates/time) from OBIS using flexible filte...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OBIS_search_occurrences(
    scientificname: Optional[str] = None,
    areaid: Optional[str] = None,
    size: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Retrieve marine species occurrence records (with coordinates/time) from OBIS using flexible filte...

    Parameters
    ----------
    scientificname : str
        Scientific name filter to restrict occurrences.
    areaid : str
        Area identifier filter (per OBIS API).
    size : int
        Number of records to return (1–100).
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
        for k, v in {
            "scientificname": scientificname,
            "areaid": areaid,
            "size": size,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OBIS_search_occurrences",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OBIS_search_occurrences"]
