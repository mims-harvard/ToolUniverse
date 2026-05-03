"""
HPA_generic_search

Generic search tool for Human Protein Atlas. Allows custom search queries and retrieval of specif...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def HPA_generic_search(
    search_query: str,
    columns: Optional[str] = None,
    format: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Generic search tool for Human Protein Atlas. Allows custom search queries and retrieval of specif...

    Parameters
    ----------
    search_query : str
        Search term for the query
    columns : str
        Comma-separated list of columns to retrieve. Defaults to 'g,gs,gd'. Common op...
    format : str
        Response format (json or tsv). Defaults to 'json'.
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
            "columns": columns,
            "format": format,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "HPA_generic_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["HPA_generic_search"]
