"""
iedb_search_bcr_sequences

Search B-cell receptor (BCR) / antibody sequence data from the IEDB. Returns antibody sequences w...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def iedb_search_bcr_sequences(
    limit: Optional[int] = 10,
    offset: Optional[int] = 0,
    select: Optional[str | list[str]] = None,
    filters: Optional[dict[str, Any]] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search B-cell receptor (BCR) / antibody sequence data from the IEDB. Returns antibody sequences w...

    Parameters
    ----------
    limit : int
        Maximum rows to return.
    offset : int
        Pagination offset.
    select : str | list[str]
        Columns to return.
    filters : dict[str, Any]
        PostgREST filters. Key columns: receptor_group_id, receptor_type, receptor_na...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "limit": limit,
            "offset": offset,
            "select": select,
            "filters": filters,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "iedb_search_bcr_sequences",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["iedb_search_bcr_sequences"]
