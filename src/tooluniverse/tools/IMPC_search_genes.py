"""
IMPC_search_genes

Search IMPC for mouse genes by symbol, name, synonym, or MGI ID. Returns matching genes with thei...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def IMPC_search_genes(
    query: str,
    limit: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search IMPC for mouse genes by symbol, name, synonym, or MGI ID. Returns matching genes with thei...

    Parameters
    ----------
    query : str
        Search query: gene symbol, name fragment, or MGI ID (e.g., 'Wdr7', 'WD repeat...
    limit : int
        Maximum results (default: 20)
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
    _args = {k: v for k, v in {"query": query, "limit": limit}.items() if v is not None}
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
