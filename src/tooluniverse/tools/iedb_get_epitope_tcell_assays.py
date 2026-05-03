"""
iedb_get_epitope_tcell_assays

Get T-cell assay data linked to a specific epitope structure ID. Given an epitope_id (from iedb_s...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def iedb_get_epitope_tcell_assays(
    epitope_id: int,
    limit: Optional[int] = 20,
    offset: Optional[int] = 0,
    select: Optional[str | list[str]] = None,
    filters: Optional[dict[str, Any]] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get T-cell assay data linked to a specific epitope structure ID. Given an epitope_id (from iedb_s...

    Parameters
    ----------
    epitope_id : int
        IEDB epitope structure ID (from iedb_search_epitopes results). Example: 20354...
    limit : int
        Maximum rows to return.
    offset : int
        Pagination offset.
    select : str | list[str]
        Columns to return.
    filters : dict[str, Any]
        Additional PostgREST filters.
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
            "epitope_id": epitope_id,
            "limit": limit,
            "offset": offset,
            "select": select,
            "filters": filters,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "iedb_get_epitope_tcell_assays",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["iedb_get_epitope_tcell_assays"]
