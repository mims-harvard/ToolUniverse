"""
Crossref_search_works

Search Crossref Works API by keyword with exact totals and deep cursor pagination. Start with the...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Crossref_search_works(
    query: str,
    limit: Optional[int] = 10,
    cursor: Optional[str] = "*",
    filter: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search Crossref Works API by keyword with exact totals and deep cursor pagination. Start with the...

    Parameters
    ----------
    query : str
        Search query for Crossref works. Use keywords separated by spaces to refine y...
    limit : int
        Number of articles to return. This sets the maximum number of articles retrie...
    cursor : str
        Crossref deep-pagination cursor. Use '*' for the first page, then metadata.ne...
    filter : str
        Optional filter string for Crossref API. Examples: 'type:journal-article' (on...
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
            "query": query,
            "limit": limit,
            "cursor": cursor,
            "filter": filter,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Crossref_search_works",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Crossref_search_works"]
