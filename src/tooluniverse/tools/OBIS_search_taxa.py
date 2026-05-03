"""
OBIS_search_taxa

Resolve marine taxa in OBIS by scientific name to obtain standardized identifiers (AphiaID), rank...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OBIS_search_taxa(
    scientificname: str,
    size: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Resolve marine taxa in OBIS by scientific name to obtain standardized identifiers (AphiaID), rank...

    Parameters
    ----------
    scientificname : str
        Scientific name query (e.g., 'Gadus').
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
        for k, v in {"scientificname": scientificname, "size": size}.items()
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
