"""
DBLP_search_publications

Search DBLP publications with offset pagination while preserving the historical list return type....
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DBLP_search_publications(
    query: str,
    limit: Optional[int] = 10,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search DBLP publications with offset pagination while preserving the historical list return type....

    Parameters
    ----------
    query : str
        Search query for DBLP publications. Use keywords separated by spaces to refin...
    limit : int
        Page size (1-1000), matching DBLP's documented h limit.
    offset : int
        Zero-based first hit (DBLP f parameter). Continue with each paper's search_pa...
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
        for k, v in {"query": query, "limit": limit, "offset": offset}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "DBLP_search_publications",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DBLP_search_publications"]
