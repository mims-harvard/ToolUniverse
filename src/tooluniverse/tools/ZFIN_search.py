"""
ZFIN_search

Search zebrafish (Danio rerio) genes in Alliance/ZFIN by symbol, synonym, name, or keyword. Retur...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ZFIN_search(
    query: str,
    limit: Optional[int] = 10,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search zebrafish (Danio rerio) genes in Alliance/ZFIN by symbol, synonym, name, or keyword. Retur...

    Parameters
    ----------
    query : str
        Gene symbol or name to search for (e.g., 'tp53', 'sox9a', 'pax2a', 'fgf8a')
    limit : int
        Maximum number of results (default: 10)
    offset : int
        Zero-based offset in the complete zebrafish gene result list. Continue with m...
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
            "name": "ZFIN_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ZFIN_search"]
