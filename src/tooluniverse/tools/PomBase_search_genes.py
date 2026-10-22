"""
PomBase_search_genes

Search all PomBase fission-yeast genes by name, systematic ID, or product keyword with complete l...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PomBase_search_genes(
    query: str,
    limit: Optional[int] = 10,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search all PomBase fission-yeast genes by name, systematic ID, or product keyword with complete l...

    Parameters
    ----------
    query : str
        Search query - gene name, systematic ID prefix, or product keyword. Examples:...
    limit : int
        Maximum results in this page (1-50, default 10).
    offset : int
        Zero-based offset in the complete filtered match list. Continue with metadata...
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
            "name": "PomBase_search_genes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PomBase_search_genes"]
