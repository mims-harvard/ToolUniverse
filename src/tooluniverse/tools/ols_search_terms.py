"""
ols_search_terms

Search terms in the EBI Ontology Lookup Service with explicit Solr offset pagination. When has_mo...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ols_search_terms(
    query: str,
    operation: Optional[str] = "search_terms",
    rows: Optional[int] = 10,
    size: Optional[int] = 10,
    ontology: Optional[str] = None,
    exact_match: Optional[bool] = False,
    include_obsolete: Optional[bool] = False,
    limit: Optional[int] = None,
    start: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search terms in the EBI Ontology Lookup Service with explicit Solr offset pagination. When has_mo...

    Parameters
    ----------
    operation : str
        The operation to perform (search_terms)
    query : str
        The search query for terms
    rows : int
        Number of results to return (default: 10). Alias: size.
    size : int
        Alias for rows. Number of results to return (default: 10).
    ontology : str
        Filter by specific ontology (optional)
    exact_match : bool
        Restrict results to exact matches (default: false). The query must equal a te...
    include_obsolete : bool
        Include obsolete terms (default: false)
    limit : int
        Alias for rows. Maximum number of results to return (default: 10, max: 100).
    start : int
        Zero-based OLS search offset. Continue with next_start while has_more is true.
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
            "operation": operation,
            "query": query,
            "rows": rows,
            "size": size,
            "ontology": ontology,
            "exact_match": exact_match,
            "include_obsolete": include_obsolete,
            "limit": limit,
            "start": start,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ols_search_terms",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ols_search_terms"]
