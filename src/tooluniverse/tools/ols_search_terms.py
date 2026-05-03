"""
ols_search_terms

Search for terms in OLS (Ontology Lookup Service)
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ols_search_terms(
    query: str,
    operation: Optional[str] = None,
    rows: Optional[int] = 10,
    size: Optional[int] = 10,
    ontology: Optional[str] = None,
    exact_match: Optional[bool] = False,
    include_obsolete: Optional[bool] = False,
    limit: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search for terms in OLS (Ontology Lookup Service)

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
        Search for exact matches only (default: false)
    include_obsolete : bool
        Include obsolete terms (default: false)
    limit : int | Any
        Alias for rows. Maximum number of results to return (default: 10, max: 100).
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
