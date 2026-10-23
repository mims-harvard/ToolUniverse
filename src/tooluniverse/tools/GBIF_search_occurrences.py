"""
GBIF_search_occurrences

Retrieve GBIF occurrence records with exact total and offset continuation. Continue with metadata...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GBIF_search_occurrences(
    taxonKey: Optional[int] = None,
    country: Optional[str] = None,
    hasCoordinate: Optional[bool] = True,
    limit: Optional[int] = 10,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Retrieve GBIF occurrence records with exact total and offset continuation. Continue with metadata...

    Parameters
    ----------
    taxonKey : int
        GBIF taxon key to filter occurrences by a specific taxon (from species search).
    country : str
        ISO 3166-1 alpha-2 country code filter (e.g., 'US', 'CN').
    hasCoordinate : bool
        Only return records with valid latitude/longitude coordinates when true.
    limit : int
        Maximum number of results to return (1–300).
    offset : int
        Zero-based offset. The wrapper enforces GBIF's current offset + limit <= 1000...
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
            "taxonKey": taxonKey,
            "country": country,
            "hasCoordinate": hasCoordinate,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GBIF_search_occurrences",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GBIF_search_occurrences"]
