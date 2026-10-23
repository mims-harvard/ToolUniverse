"""
DOAJ_search_articles

Search DOAJ for open-access articles or journals with exact recoverable pagination. Start with pa...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DOAJ_search_articles(
    query: str,
    max_results: Optional[int] = 10,
    page: Optional[int] = 1,
    type_: Optional[str] = "articles",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search DOAJ for open-access articles or journals with exact recoverable pagination. Start with pa...

    Parameters
    ----------
    query : str
        Search query for DOAJ articles. Supports Lucene syntax for advanced queries.
    max_results : int
        Number of results per page (1-100). Out-of-range values are rejected rather t...
    page : int
        One-based result page. Continue with metadata.next_page while metadata.has_mo...
    type_ : str
        Type of search: 'articles' or 'journals'. Default is 'articles'.
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
            "max_results": max_results,
            "page": page,
            "type": type_,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "DOAJ_search_articles",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DOAJ_search_articles"]
