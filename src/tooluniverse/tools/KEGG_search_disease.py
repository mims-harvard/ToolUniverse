"""
KEGG_search_disease

Search the KEGG DISEASE database by keyword. KEGG DISEASE contains 2,600+ human disease entries w...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def KEGG_search_disease(
    keyword: Optional[str] = None,
    max_results: Optional[int] = 25,
    query: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search the KEGG DISEASE database by keyword. KEGG DISEASE contains 2,600+ human disease entries w...

    Parameters
    ----------
    keyword : str
        Search keyword for disease name (e.g., 'leukemia', 'diabetes', 'breast cancer...
    max_results : int
        Maximum number of results to return (default: 25).
    query : str | Any
        Alias for keyword: search keyword for disease name (e.g., 'diabetes', 'leukem...
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
            "keyword": keyword,
            "max_results": max_results,
            "query": query,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "KEGG_search_disease",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["KEGG_search_disease"]
