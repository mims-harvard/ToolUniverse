"""
iCite_search_publications

Search PubMed publications by query and get citation metrics from NIH's iCite API. Returns papers...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def iCite_search_publications(
    query: str,
    limit: Optional[int | Any] = None,
    offset: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search PubMed publications by query and get citation metrics from NIH's iCite API. Returns papers...

    Parameters
    ----------
    query : str
        Search query for PubMed (e.g., 'BRCA1 cancer', 'COVID-19 vaccine efficacy', '...
    limit : int | Any
        Maximum number of results (default 10, max 1000)
    offset : int | Any
        Offset for pagination (default 0)
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
        for k, v in {"query": query, "limit": limit, "offset": offset}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "iCite_search_publications",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["iCite_search_publications"]
