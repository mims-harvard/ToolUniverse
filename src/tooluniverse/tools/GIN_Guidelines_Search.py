"""
GIN_Guidelines_Search

Search Guidelines International Network (GIN) guidelines database. GIN maintains the world's larg...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GIN_Guidelines_Search(
    query: str,
    limit: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search Guidelines International Network (GIN) guidelines database. GIN maintains the world's larg...

    Parameters
    ----------
    query : str
        Medical condition, treatment, or clinical topic to search for in GIN guidelin...
    limit : int
        Maximum number of guidelines to return (default: 10)
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
        {
            "name": "GIN_Guidelines_Search",
            "arguments": {"query": query, "limit": limit},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GIN_Guidelines_Search"]
