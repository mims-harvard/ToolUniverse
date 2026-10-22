"""
DepMap_search_genes

Search the full DepMap/Sanger gene catalog by exact symbol or symbol prefix. Prefix matches spann...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DepMap_search_genes(
    query: str,
    limit: Optional[int] = 20,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search the full DepMap/Sanger gene catalog by exact symbol or symbol prefix. Prefix matches spann...

    Parameters
    ----------
    query : str
        Gene symbol or name to search (e.g., 'WDR7', 'EGFR', 'TP53')
    limit : int
        Number of matching genes per page (1-500; default 20).
    offset : int
        Zero-based offset into the complete prefix match set.
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
        for k, v in {"query": query, "limit": limit, "offset": offset}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "DepMap_search_genes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DepMap_search_genes"]
