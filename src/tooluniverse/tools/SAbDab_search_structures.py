"""
SAbDab_search_structures

Search SAbDab structural antibody database. Returns a direct browse URL to matching antibody stru...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SAbDab_search_structures(
    operation: Optional[str] = None,
    query: Optional[str] = None,
    antigen: Optional[str] = None,
    limit: Optional[int] = 50,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search SAbDab structural antibody database. Returns a direct browse URL to matching antibody stru...

    Parameters
    ----------
    operation : str

    query : str
        Search query - antigen name, species, or keywords (e.g., 'HER2', 'anti-CD20')
    antigen : str
        Alias for query. Antigen name to search (e.g., 'EGFR', 'HER2').
    limit : int
        Maximum results (default: 50)
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
            "antigen": antigen,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "SAbDab_search_structures",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SAbDab_search_structures"]
