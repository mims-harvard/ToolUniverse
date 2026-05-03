"""
umls_search_concepts

Search for concepts in UMLS (Unified Medical Language System) using concept names or terms. UMLS ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def umls_search_concepts(
    query: str,
    sabs: Optional[str] = None,
    pageNumber: Optional[int] = 1,
    pageSize: Optional[int] = 25,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search for concepts in UMLS (Unified Medical Language System) using concept names or terms. UMLS ...

    Parameters
    ----------
    query : str
        Search query (concept name or term)
    sabs : str
        Source abbreviation(s) to filter by (e.g., 'SNOMEDCT_US', 'ICD10CM', 'LOINC',...
    pageNumber : int
        Page number for pagination (default: 1)
    pageSize : int
        Number of results per page (default: 25, max: 25)
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

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "query": query,
            "sabs": sabs,
            "pageNumber": pageNumber,
            "pageSize": pageSize,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "umls_search_concepts",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["umls_search_concepts"]
