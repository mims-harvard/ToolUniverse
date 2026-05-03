"""
EMDB_search_structures

Search the Electron Microscopy Data Bank (EMDB) for cryo-EM structures using keywords. Returns a ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EMDB_search_structures(
    query: str,
    rows: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search the Electron Microscopy Data Bank (EMDB) for cryo-EM structures using keywords. Returns a ...

    Parameters
    ----------
    query : str
        Search query for EMDB structures. Examples: 'ribosome', 'spike protein', 'SAR...
    rows : int
        Maximum number of search results to return (default: 10, max: 1000).
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
    _args = {k: v for k, v in {"query": query, "rows": rows}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "EMDB_search_structures",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EMDB_search_structures"]
