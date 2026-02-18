"""
get_patent_overview_by_text_query

Search for patent application overviews using a query string of the format 'applicationMetaData.i...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def get_patent_overview_by_text_query(
    query: str,
    exact_match: Optional[bool] = False,
    sort: Optional[str] = "filingDate desc",
    offset: Optional[int] = 0,
    limit: Optional[int] = 25,
    rangeFilters: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search for patent application overviews using a query string of the format 'applicationMetaData.i...

    Parameters
    ----------
    query : str
        Keyword or keyphrase to search for in the patent application title. This fiel...
    exact_match : bool
        If true, the search will only return results that exactly match the provided ...
    sort : str
        Sorts results by one of the following fields: filingDate or grantDate. Follow...
    offset : int
        The starting position (zero-indexed) of the result set. Default is 0.
    limit : int
        The maximum number of results to return. Default is 25.
    rangeFilters : str
        Limits results to the date range specified for one of the following fields: f...
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

    return get_shared_client().run_one_function(
        {
            "name": "get_patent_overview_by_text_query",
            "arguments": {
                "query": query,
                "exact_match": exact_match,
                "sort": sort,
                "offset": offset,
                "limit": limit,
                "rangeFilters": rangeFilters,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["get_patent_overview_by_text_query"]
