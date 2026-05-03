"""
iedb_get_epitope_antigens

Given an epitope `structure_id`, get linked antigens (IEDB Query API). Returned rows contain `par...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def iedb_get_epitope_antigens(
    structure_id: int,
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
    Given an epitope `structure_id`, get linked antigens (IEDB Query API). Returned rows contain `par...

    Parameters
    ----------
    structure_id : int
        IEDB epitope structure ID (from `iedb_search_epitopes`).
    limit : int
        Maximum number of rows to return.
    offset : int
        Pagination offset.
    order : str
        Optional PostgREST order clause.
    select : str
        Optional projection list (comma-separated string or array of field names).
    filters : dict[str, Any]
        Advanced PostgREST filters mapping column -> filter expression.
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
            "structure_id": structure_id,
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
            "name": "iedb_get_epitope_antigens",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["iedb_get_epitope_antigens"]
