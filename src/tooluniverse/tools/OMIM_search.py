"""
OMIM_search

Search OMIM database for Mendelian diseases and genes. OMIM is the authoritative source for human...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OMIM_search(
    operation: str,
    query: str,
    limit: Optional[int] = 10,
    start: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search OMIM database for Mendelian diseases and genes. OMIM is the authoritative source for human...

    Parameters
    ----------
    operation : str
        Operation type (fixed: search)
    query : str
        Search query - gene name (BRCA1), disease (cystic fibrosis), or phenotype (in...
    limit : int
        Maximum results (default: 10, max: 20)
    start : int
        Offset for pagination (default: 0)
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

    return get_shared_client().run_one_function(
        {
            "name": "OMIM_search",
            "arguments": {
                "operation": operation,
                "query": query,
                "limit": limit,
                "start": start,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OMIM_search"]
