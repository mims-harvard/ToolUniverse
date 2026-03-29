"""
SemanticScholar_search_papers

Search for papers on Semantic Scholar including abstracts and AI-generated TLDR summaries. This t...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SemanticScholar_search_papers(
    query: str,
    limit: Optional[int] = 5,
    year: Optional[str] = None,
    sort: Optional[str] = None,
    include_abstract: Optional[bool] = False,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search for papers on Semantic Scholar including abstracts and AI-generated TLDR summaries. This t...

    Parameters
    ----------
    query : str
        Search query for Semantic Scholar. Use keywords separated by spaces to refine...
    limit : int
        Maximum number of papers to return from Semantic Scholar.
    year : str
        Filter results by publication year. Use a single year (e.g., '2024') or a ran...
    sort : str
        Sort results. Options: 'citationCount:desc', 'citationCount:asc', 'publicatio...
    include_abstract : bool
        If true, best-effort fetches missing abstracts via the paper detail endpoint ...
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
        for k, v in {
            "query": query,
            "limit": limit,
            "year": year,
            "sort": sort,
            "include_abstract": include_abstract,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "SemanticScholar_search_papers",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SemanticScholar_search_papers"]
