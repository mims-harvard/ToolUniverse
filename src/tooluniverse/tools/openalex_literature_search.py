"""
openalex_literature_search

Search for academic literature using OpenAlex. Supports optional full-text-index filtering (has_f...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def openalex_literature_search(
    search_keywords: Optional[str] = None,
    query: Optional[str] = None,
    max_results: Optional[int] = 10,
    limit: Optional[int] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    open_access: Optional[bool] = None,
    require_has_fulltext: Optional[bool] = False,
    fulltext_terms: Optional[list[str]] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search for academic literature using OpenAlex. Supports optional full-text-index filtering (has_f...

    Parameters
    ----------
    search_keywords : str
        Keywords to search for in paper titles/abstracts/etc. For full-text-index-onl...
    query : str
        Alias for `search_keywords` (recommended when you standardize on `query` acro...
    max_results : int
        Maximum number of papers to retrieve (default: 10, maximum: 200).
    limit : int
        Alias for `max_results` (OpenAlex max 200).
    year_from : int
        Start year for publication date filter (e.g., 2020). Optional parameter to li...
    year_to : int
        End year for publication date filter (e.g., 2023). Optional parameter to limi...
    open_access : bool
        Filter for open access papers only. Set to true for open access papers, false...
    require_has_fulltext : bool
        If true, filters to works where OpenAlex indicates a full-text index is avail...
    fulltext_terms : list[str]
        Optional list of terms that must occur in OpenAlex full-text index (adds full...
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
            "search_keywords": search_keywords,
            "query": query,
            "max_results": max_results,
            "limit": limit,
            "year_from": year_from,
            "year_to": year_to,
            "open_access": open_access,
            "require_has_fulltext": require_has_fulltext,
            "fulltext_terms": fulltext_terms,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "openalex_literature_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["openalex_literature_search"]
