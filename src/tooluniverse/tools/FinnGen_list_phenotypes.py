"""
FinnGen_list_phenotypes

Search and list FinnGen disease endpoints (phenotypes). FinnGen is a Finnish population genomics ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FinnGen_list_phenotypes(
    query: Optional[str | Any] = None,
    category: Optional[str | Any] = None,
    min_cases: Optional[int | Any] = None,
    limit: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search and list FinnGen disease endpoints (phenotypes). FinnGen is a Finnish population genomics ...

    Parameters
    ----------
    query : str | Any
        Search query to filter phenotypes by code, name, or category (e.g., 'diabetes...
    category : str | Any
        Filter by disease category (e.g., 'Diabetes', 'circulatory', 'Neoplasms'). Ca...
    min_cases : int | Any
        Minimum number of cases required. Use to filter for well-powered phenotypes (...
    limit : int | Any
        Maximum number of results to return (default 50).
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
            "category": category,
            "min_cases": min_cases,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "FinnGen_list_phenotypes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FinnGen_list_phenotypes"]
