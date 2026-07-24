"""
IPD_search_cells

Search IPD cell lines (HLA reference cells with their HLA typing) by a field value. By default se...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def IPD_search_cells(
    query: str,
    field: Optional[str] = "primary_name",
    match_: Optional[str] = "contains",
    limit: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search IPD cell lines (HLA reference cells with their HLA typing) by a field value. By default se...

    Parameters
    ----------
    query : str
        Text to search for (e.g. a cell primary name, or a lab name when field='lab_o...
    field : str
        Cell field to search (default 'primary_name'). Other useful fields include 'l...
    match_ : str
        How to match: 'contains' (default, substring), 'startsWith' (prefix), or 'eq'...
    limit : int
        Maximum number of cells to return (default 10, max 100).
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
            "query": query,
            "field": field,
            "match": match_,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "IPD_search_cells",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["IPD_search_cells"]
