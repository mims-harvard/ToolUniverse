"""
DOAJ_search_articles

Search DOAJ (Directory of Open Access Journals) for open-access articles. Returns articles with t...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DOAJ_search_articles(
    query: str,
    max_results: Optional[int] = 10,
    type_: Optional[str] = "articles",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search DOAJ (Directory of Open Access Journals) for open-access articles. Returns articles with t...

    Parameters
    ----------
    query : str
        Search query for DOAJ articles. Supports Lucene syntax for advanced queries.
    max_results : int
        Maximum number of articles to return. Default is 10, maximum is 100.
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

    return get_shared_client().run_one_function(
        {
            "name": "DOAJ_search_articles",
            "arguments": {"query": query, "max_results": max_results, "type": type_},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DOAJ_search_articles"]
