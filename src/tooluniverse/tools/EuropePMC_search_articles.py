"""
EuropePMC_search_articles

Search for articles on Europe PMC including abstracts and metadata. Europe PMC supports fielded q...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EuropePMC_search_articles(
    query: str,
    limit: Optional[int] = 5,
    require_has_ft: Optional[bool] = False,
    fulltext_terms: Optional[list[str]] = None,
    enrich_missing_abstract: Optional[bool] = False,
    extract_terms_from_fulltext: Optional[list[str]] = None,
    page_size: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search for articles on Europe PMC including abstracts and metadata. Europe PMC supports fielded q...

    Parameters
    ----------
    query : str
        Search query for Europe PMC. Supports Lucene-like fielded syntax (e.g., BODY:...
    limit : int
        Number of articles to return. This sets the maximum number of articles retrie...
    require_has_ft : bool
        If true, appends `HAS_FT:Y` to the query to restrict results to records where...
    fulltext_terms : list[str]
        Optional list of terms that must occur in the indexed full text (Europe PMC B...
    enrich_missing_abstract : bool
        If true, best-effort fills missing abstracts by fetching Europe PMC fullTextX...
    extract_terms_from_fulltext : list[str]
        Optional list of terms to extract from full text (open access only). When pro...
    page_size : int
        Alias for limit — number of results to return
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
            "require_has_ft": require_has_ft,
            "fulltext_terms": fulltext_terms,
            "enrich_missing_abstract": enrich_missing_abstract,
            "extract_terms_from_fulltext": extract_terms_from_fulltext,
            "page_size": page_size,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EuropePMC_search_articles",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EuropePMC_search_articles"]
