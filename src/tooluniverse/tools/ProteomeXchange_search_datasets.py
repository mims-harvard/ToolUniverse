"""
ProteomeXchange_search_datasets

Search the complete ProteomeXchange/ProteomeCentral dataset catalog. The upstream CGI ignores its...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ProteomeXchange_search_datasets(
    query: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the complete ProteomeXchange/ProteomeCentral dataset catalog. The upstream CGI ignores its...

    Parameters
    ----------
    query : str
        Optional case-insensitive search filter applied across accession, title, spec...
    limit : int
        Maximum results to return (1-1000, default 10).
    offset : int
        Zero-based offset into the complete locally filtered result set (default 0). ...
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
            "name": "ProteomeXchange_search_datasets",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ProteomeXchange_search_datasets"]
