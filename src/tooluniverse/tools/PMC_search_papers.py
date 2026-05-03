"""
PMC_search_papers

Search for full-text biomedical literature using the PMC (PubMed Central) API. PMC is the free fu...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PMC_search_papers(
    query: str,
    limit: Optional[int] = 10,
    retmax: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    article_type: Optional[str] = None,
    include_abstract: Optional[bool] = False,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search for full-text biomedical literature using the PMC (PubMed Central) API. PMC is the free fu...

    Parameters
    ----------
    query : str
        Search query for PMC papers. Use keywords separated by spaces to refine your ...
    limit : int
        Maximum number of papers to return. This sets the maximum number of papers re...
    retmax : int
        Alias for limit (NCBI eutils naming). If both retmax and limit are provided, ...
    date_from : str
        Start date for publication date filter (YYYY/MM/DD format). Optional paramete...
    date_to : str
        End date for publication date filter (YYYY/MM/DD format). Optional parameter ...
    article_type : str
        Article type filter (e.g., 'research-article', 'review', 'case-report'). Opti...
    include_abstract : bool
        If true, attempts to enrich results with an abstract (best-effort) by fetchin...
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
            "limit": limit,
            "retmax": retmax,
            "date_from": date_from,
            "date_to": date_to,
            "article_type": article_type,
            "include_abstract": include_abstract,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PMC_search_papers",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PMC_search_papers"]
