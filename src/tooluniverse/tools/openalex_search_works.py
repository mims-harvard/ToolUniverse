"""
openalex_search_works

Search OpenAlex works (papers) via the /works endpoint. Supports both general search and optional...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def openalex_search_works(
    search: Optional[str] = None,
    query: Optional[str] = None,
    filter: Optional[str] = None,
    require_has_fulltext: Optional[bool] = False,
    fulltext_terms: Optional[list[str]] = None,
    per_page: Optional[int] = 10,
    limit: Optional[int] = None,
    page: Optional[int] = 1,
    sort: Optional[str] = None,
    mailto: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Optional[dict[str, Any]]:
    """
    Search OpenAlex works (papers) via the /works endpoint. Supports both general search and optional...

    Parameters
    ----------
    search : str
        Search query for works. Use filter + fulltext_terms/require_has_fulltext when...
    query : str
        Alias for `search` (recommended when you standardize on `query` across multip...
    filter : str
        OpenAlex filter string (comma-separated). Example: "from_publication_date:202...
    require_has_fulltext : bool
        If true, appends OpenAlex filter has_fulltext:true (keeps only works with ful...
    fulltext_terms : list[str]
        Optional list of terms to match in OpenAlex full-text index. Adds one or more...
    per_page : int
        Results per page (OpenAlex max 200).
    limit : int
        Alias for `per_page` (OpenAlex max 200).
    page : int
        Page number (1-indexed).
    sort : str
        Sort order string, e.g. "cited_by_count:desc".
    mailto : str
        Optional contact email for OpenAlex polite pool. If omitted, ToolUniverse use...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    Optional[dict[str, Any]]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "search": search,
            "query": query,
            "filter": filter,
            "require_has_fulltext": require_has_fulltext,
            "fulltext_terms": fulltext_terms,
            "per_page": per_page,
            "limit": limit,
            "page": page,
            "sort": sort,
            "mailto": mailto,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "openalex_search_works",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["openalex_search_works"]
