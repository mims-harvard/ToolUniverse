"""
CORE_search_papers

Search for open access academic papers using CORE API. CORE aggregates OA repository and journal ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CORE_search_papers(
    query: Optional[str] = None,
    search: Optional[str] = None,
    q: Optional[str] = None,
    limit: Optional[int] = 10,
    page_size: Optional[int] = None,
    max_results: Optional[int] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    language: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search for open access academic papers using CORE API. CORE aggregates OA repository and journal ...

    Parameters
    ----------
    query : str
        Search query for CORE papers. Use keywords separated by spaces to refine your...
    search : str
        Alias for `query`.
    q : str
        Alias for `query`.
    limit : int
        Maximum number of papers to return. This sets the maximum number of papers re...
    page_size : int
        Alias for `limit`.
    max_results : int
        Alias for `limit`.
    year_from : int
        Start year for publication date filter (e.g., 2020). Optional parameter to li...
    year_to : int
        End year for publication date filter (e.g., 2024). Optional parameter to limi...
    language : str
        Language filter for papers (e.g., 'en', 'es', 'fr'). Optional parameter to li...
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
            "search": search,
            "q": q,
            "limit": limit,
            "page_size": page_size,
            "max_results": max_results,
            "year_from": year_from,
            "year_to": year_to,
            "language": language,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "CORE_search_papers",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CORE_search_papers"]
