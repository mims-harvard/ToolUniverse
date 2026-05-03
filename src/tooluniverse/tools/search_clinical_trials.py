"""
search_clinical_trials

Search ClinicalTrials.gov for clinical trials by disease/condition, drug/intervention, or keyword...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def search_clinical_trials(
    condition: Optional[str] = None,
    intervention: Optional[str] = None,
    query_term: Optional[str] = None,
    pageSize: Optional[int] = None,
    pageToken: Optional[str] = None,
    overall_status: Optional[list[str]] = None,
    max_results: Optional[int] = None,
    limit: Optional[int] = None,
    status: Optional[str | list[str]] = None,
    keyword: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search ClinicalTrials.gov for clinical trials by disease/condition, drug/intervention, or keyword...

    Parameters
    ----------
    condition : str
        Query for condition or disease using Essie expression syntax (e.g., 'lung can...
    intervention : str
        Query for intervention/treatment using Essie expression syntax (e.g., 'chemot...
    query_term : str
        Query for 'other terms' with Essie expression syntax (e.g., 'combination', 'A...
    pageSize : int
        Maximum number of studies to return per page (default 10, max 1000).
    pageToken : str
        Token to retrieve the next page of results, obtained from the 'nextPageToken'...
    overall_status : list[str]
        Filter by overall study status (e.g., ['RECRUITING'], ['COMPLETED'], ['RECRUI...
    max_results : int
        Maximum number of studies to return (alias for pageSize, default 10, max 1000).
    limit : int
        Alias for max_results: maximum number of studies to return (default 10, max 1...
    status : str | list[str]
        Alias for overall_status. Filter by trial status, e.g. "RECRUITING", "COMPLET...
    keyword : str
        Alias for query_term. Free-text keyword search across all trial fields (e.g.,...
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
            "condition": condition,
            "intervention": intervention,
            "query_term": query_term,
            "pageSize": pageSize,
            "pageToken": pageToken,
            "overall_status": overall_status,
            "max_results": max_results,
            "limit": limit,
            "status": status,
            "keyword": keyword,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "search_clinical_trials",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["search_clinical_trials"]
