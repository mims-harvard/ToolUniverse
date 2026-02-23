"""
Figshare_search_articles

Search Figshare for research outputs (datasets, figures, code, posters, papers, theses, presentat...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Figshare_search_articles(
    search_for: str,
    item_type: Optional[int | Any] = None,
    page_size: Optional[int | Any] = None,
    published_since: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search Figshare for research outputs (datasets, figures, code, posters, papers, theses, presentat...

    Parameters
    ----------
    search_for : str
        Keyword search query (e.g., 'CRISPR knockout RNA-seq', 'protein structure cry...
    item_type : int | Any
        Filter by item type: 3=dataset, 2=media, 1=figure, 9=code, 7=thesis, 6=book, ...
    page_size : int | Any
        Number of results (default 10, max 1000)
    published_since : str | Any
        Filter to articles published after this date in format 'YYYY-MM-DD' (e.g., '2...
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

    return get_shared_client().run_one_function(
        {
            "name": "Figshare_search_articles",
            "arguments": {
                "search_for": search_for,
                "item_type": item_type,
                "page_size": page_size,
                "published_since": published_since,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Figshare_search_articles"]
