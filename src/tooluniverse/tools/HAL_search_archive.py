"""
HAL_search_archive

Search the French HAL open archive via its public API. Returns documents with title, authors, yea...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def HAL_search_archive(
    query: str,
    max_results: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search the French HAL open archive via its public API. Returns documents with title, authors, yea...

    Parameters
    ----------
    query : str
        Search query for HAL archive. Supports Lucene syntax for advanced queries.
    max_results : int
        Maximum number of documents to return. Default is 10, maximum is 100.
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
        for k, v in {"query": query, "max_results": max_results}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "HAL_search_archive",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["HAL_search_archive"]
