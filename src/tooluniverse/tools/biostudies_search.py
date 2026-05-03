"""
biostudies_search

Search BioStudies repository for biological studies across all collections. BioStudies is a compr...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def biostudies_search(
    query: Optional[str] = None,
    pageSize: Optional[int] = 10,
    page: Optional[int] = 1,
    sortBy: Optional[str] = None,
    sortOrder: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search BioStudies repository for biological studies across all collections. BioStudies is a compr...

    Parameters
    ----------
    query : str
        Search query (supports keywords, phrases, and Boolean operators). Use '*' for...
    pageSize : int
        Number of results per page (default: 10, max: 100)
    page : int
        Page number for pagination (default: 1, 1-based)
    sortBy : str
        Sort field (e.g., 'relevance', 'accession', 'release_date')
    sortOrder : str
        Sort order: 'ascending' or 'descending'
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "query": query,
            "pageSize": pageSize,
            "page": page,
            "sortBy": sortBy,
            "sortOrder": sortOrder,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "biostudies_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["biostudies_search"]
