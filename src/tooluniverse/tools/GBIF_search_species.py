"""
GBIF_search_species

Find taxa by keyword (scientific/common names) in GBIF. Use to resolve organism names to stable t...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GBIF_search_species(
    query: str,
    limit: Optional[int] = 10,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Find taxa by keyword (scientific/common names) in GBIF. Use to resolve organism names to stable t...

    Parameters
    ----------
    query : str
        Search string for species/taxa (supports scientific/common names), e.g., 'Hom...
    limit : int
        Maximum number of results to return (1–300).
    offset : int
        Result offset for pagination (0-based).
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
        for k, v in {"query": query, "limit": limit, "offset": offset}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GBIF_search_species",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GBIF_search_species"]
