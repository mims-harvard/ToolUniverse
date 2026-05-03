"""
PubMed_search_articles

Search PubMed biomedical literature database using NCBI E-utilities (esearch + esummary). Returns...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PubMed_search_articles(
    query: str,
    limit: Optional[int] = 10,
    mindate: Optional[str] = None,
    maxdate: Optional[str] = None,
    datetype: Optional[str] = "pdat",
    include_abstract: Optional[bool] = False,
    sort: Optional[str] = None,
    max_results: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search PubMed biomedical literature database using NCBI E-utilities (esearch + esummary). Returns...

    Parameters
    ----------
    query : str
        Search query for PubMed articles. Use keywords, author names, journal names, ...
    limit : int
        Number of articles to return. This sets the maximum number of articles retrie...
    mindate : str
        Minimum date for results (format: YYYY/MM/DD or YYYY). Requires datetype to b...
    maxdate : str
        Maximum date for results (format: YYYY/MM/DD or YYYY). Requires datetype to b...
    datetype : str
        Type of date to filter on: 'pdat' (publication date), 'edat' (Entrez date), o...
    include_abstract : bool
        If true, best-effort fetches abstracts via efetch (adds abstract/abstract_sou...
    sort : str
        Sort order for results. Valid values: 'pub_date' (newest first), 'Author' (al...
    max_results : int
        Alias for limit — maximum number of results to return
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
            "mindate": mindate,
            "maxdate": maxdate,
            "datetype": datetype,
            "include_abstract": include_abstract,
            "sort": sort,
            "max_results": max_results,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PubMed_search_articles",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PubMed_search_articles"]
