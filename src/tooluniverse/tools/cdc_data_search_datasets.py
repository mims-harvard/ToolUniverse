"""
cdc_data_search_datasets

Search for datasets on Data.CDC.gov (CDC's Socrata-based open data portal). Returns a list of ava...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def cdc_data_search_datasets(
    search_query: Optional[str] = None,
    category: Optional[str] = None,
    limit: Optional[int] = 50,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search for datasets on Data.CDC.gov (CDC's Socrata-based open data portal). Returns a list of ava...

    Parameters
    ----------
    search_query : str
        Search term to find datasets (e.g., 'mortality', 'vaccination', 'covid')
    category : str
        Optional category filter (e.g., 'Health', 'Public Safety')
    limit : int
        Maximum number of datasets to return (default: 50, max: 1000)
    offset : int
        Number of results to skip for pagination (default: 0)
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
            "search_query": search_query,
            "category": category,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "cdc_data_search_datasets",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["cdc_data_search_datasets"]
