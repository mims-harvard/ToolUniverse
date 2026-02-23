"""
MeSH_search_terms

Search MeSH terms (entry terms/synonyms) by label. MeSH terms include the preferred descriptor na...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MeSH_search_terms(
    query: str,
    match_: Optional[str | Any] = None,
    limit: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search MeSH terms (entry terms/synonyms) by label. MeSH terms include the preferred descriptor na...

    Parameters
    ----------
    query : str
        Term label to search for. Examples: 'tumor', 'heart attack', 'aspirin', 'bloo...
    match_ : str | Any
        Match type: 'exact' for exact match, 'contains' for partial match (default), ...
    limit : int | Any
        Maximum number of results (default: 20, max: 50).
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
            "name": "MeSH_search_terms",
            "arguments": {"query": query, "match": match_, "limit": limit},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MeSH_search_terms"]
