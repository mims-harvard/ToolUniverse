"""
PROSITE_search

Search the PROSITE database for protein motifs, domains, and functional site patterns by keyword....
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PROSITE_search(
    query: str,
    limit: Optional[int] = None,
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
        Maximum number of results to return (default: 10, max: 50).
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

    return get_shared_client().run_one_function(
        {"name": "PROSITE_search", "arguments": {"query": query, "limit": limit}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PROSITE_search"]
