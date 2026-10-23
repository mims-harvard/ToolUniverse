"""
PROSITE_search

Search the PROSITE database for protein motifs, domains, and functional site patterns by keyword....
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PROSITE_search(
    query: str,
    limit: Optional[int] = 10,
    cursor: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the PROSITE database for protein motifs, domains, and functional site patterns by keyword....

    Parameters
    ----------
    query : str
        Search keyword(s) for PROSITE entries. Examples: 'zinc finger', 'kinase', 'gl...
    limit : int
        Number of results per page (1-1000). Values outside this range are rejected r...
    cursor : str
        Opaque InterPro pagination cursor. Omit for the first page; for later pages, ...
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
        for k, v in {"query": query, "limit": limit, "cursor": cursor}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PROSITE_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PROSITE_search"]
