"""
ArXiv_search_papers

Search arXiv using the public Atom API with exact OpenSearch totals and recoverable start paginat...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ArXiv_search_papers(
    query: str,
    limit: Optional[int] = 10,
    start: Optional[int] = 0,
    sort_by: Optional[str] = "relevance",
    sort_order: Optional[str] = "descending",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search arXiv using the public Atom API with exact OpenSearch totals and recoverable start paginat...

    Parameters
    ----------
    query : str
        Search query for arXiv papers. Unquoted, unprefixed space-separated keywords ...
    limit : int
        Number of papers to return (1-200). This sets the maximum number of papers re...
    start : int
        Zero-based result offset. For the next page, add the number of papers returne...
    sort_by : str
        Sort order for results. Options: 'relevance', 'lastUpdatedDate', 'submittedDate'
    sort_order : str
        Sort direction. Options: 'ascending', 'descending'
    date_from : str
        Filter results from this date (format: YYYY-MM-DD). Uses submittedDate, the d...
    date_to : str
        Filter results up to this date (format: YYYY-MM-DD). Uses submittedDate, the ...
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
            "start": start,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "date_from": date_from,
            "date_to": date_to,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ArXiv_search_papers",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ArXiv_search_papers"]
