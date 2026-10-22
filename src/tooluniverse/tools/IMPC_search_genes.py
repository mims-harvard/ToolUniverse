"""
IMPC_search_genes

Search IMPC mouse genes by symbol, name, synonym, or MGI ID with exact Solr offset pagination. Co...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def IMPC_search_genes(
    query: str,
    limit: Optional[int] = 20,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search IMPC mouse genes by symbol, name, synonym, or MGI ID with exact Solr offset pagination. Co...

    Parameters
    ----------
    query : str
        Search query: gene symbol, name fragment, or MGI ID (e.g., 'Wdr7', 'WD repeat...
    limit : int
        Maximum results (default: 20)
    offset : int
        Zero-based result offset. Continue with data.next_offset.
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
        for k, v in {"query": query, "limit": limit, "offset": offset}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "IMPC_search_genes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["IMPC_search_genes"]
