"""
CEDA_search_datasets

Search the CEDA environmental data catalogue with a real case-insensitive Django filter over one ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CEDA_search_datasets(
    q: Optional[str] = None,
    search_field: Optional[str] = "title",
    limit: Optional[int] = 10,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the CEDA environmental data catalogue with a real case-insensitive Django filter over one ...

    Parameters
    ----------
    q : str
        Case-insensitive substring applied to search_field. Omit to list all observat...
    search_field : str
        Single CEDA field searched by q; the API cannot OR across these fields.
    limit : int
        Number of results to return (default 10, max 100)
    offset : int
        Offset for pagination
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
            "q": q,
            "search_field": search_field,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "CEDA_search_datasets",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CEDA_search_datasets"]
