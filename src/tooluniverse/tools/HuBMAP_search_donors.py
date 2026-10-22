"""
HuBMAP_search_donors

Search HuBMAP human Donors with normalized demographics, exact totals, and Elasticsearch offset p...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def HuBMAP_search_donors(
    group_name: Optional[str] = None,
    query: Optional[str] = None,
    limit: Optional[int] = 10,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search HuBMAP human Donors with normalized demographics, exact totals, and Elasticsearch offset p...

    Parameters
    ----------
    group_name : str
        Filter by the data-providing group/TMC name (partial match, e.g. 'Stanford', ...
    query : str
        Free-text search across donor description and demographic values (e.g. 'femal...
    limit : int
        Maximum number of results (1-50, default 10).
    offset : int
        Number of matching donors to skip. Continue with metadata.next_offset.
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
            "group_name": group_name,
            "query": query,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "HuBMAP_search_donors",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["HuBMAP_search_donors"]
