"""
GBIF_get_vernacular_names

Get de-duplicated vernacular names of a GBIF Backbone taxon, optionally filtered by language. GBI...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GBIF_get_vernacular_names(
    taxon_key: int,
    language: Optional[str] = None,
    limit: Optional[int] = 100,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get de-duplicated vernacular names of a GBIF Backbone taxon, optionally filtered by language. GBI...

    Parameters
    ----------
    taxon_key : int
        GBIF Backbone usageKey of the taxon, e.g. 5219404 (Panthera leo). Obtain from...
    language : str
        Optional ISO 639-3 language code to filter by, e.g. 'eng' (English), 'spa' (S...
    limit : int
        Number of raw GBIF vernacular-name records to inspect per page.
    offset : int
        Zero-based raw GBIF result offset. Continue with metadata.next_offset even wh...
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
            "taxon_key": taxon_key,
            "language": language,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GBIF_get_vernacular_names",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GBIF_get_vernacular_names"]
