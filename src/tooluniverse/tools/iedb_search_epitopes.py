"""
iedb_search_epitopes

Search immune epitopes (IEDB Query API). Use this to discover epitope `structure_id` values, then...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def iedb_search_epitopes(
    sequence_contains: Optional[str] = None,
    structure_type: Optional[str] = None,
    limit: Optional[int] = 10,
    offset: Optional[int] = 0,
    order: Optional[str] = None,
    select: Optional[str] = None,
    filters: Optional[dict[str, Any]] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search immune epitopes (IEDB Query API). Use this to discover epitope `structure_id` values, then...

    Parameters
    ----------
    sequence_contains : str
        Sequence fragment to search within `linear_sequence` using a contains match. ...
    structure_type : str
        Filter by epitope structure type. Example: 'Linear peptide'.
    limit : int
        Maximum number of rows to return.
    offset : int
        Pagination offset.
    order : str
        Optional PostgREST order clause (e.g., 'structure_id.asc').
    select : str
        Optional projection list to reduce payload size. Provide a comma-separated st...
    filters : dict[str, Any]
        Advanced PostgREST filters mapping column -> filter expression (e.g., {"linea...
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
            "sequence_contains": sequence_contains,
            "structure_type": structure_type,
            "limit": limit,
            "offset": offset,
            "order": order,
            "select": select,
            "filters": filters,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "iedb_search_epitopes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["iedb_search_epitopes"]
