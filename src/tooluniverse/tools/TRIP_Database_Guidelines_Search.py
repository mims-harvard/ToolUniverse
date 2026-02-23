"""
TRIP_Database_Guidelines_Search

Search TRIP Database (Turning Research into Practice) for evidence-based clinical guidelines. TRI...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def TRIP_Database_Guidelines_Search(
    query: str,
    limit: int,
    search_type: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search TRIP Database (Turning Research into Practice) for evidence-based clinical guidelines. TRI...

    Parameters
    ----------
    query : str
        Medical condition, treatment, or clinical question (e.g., 'diabetes managemen...
    limit : int
        Maximum number of guidelines to return (default: 10)
    search_type : str
        Type of content to search for (default: 'guideline'). Options include 'guidel...
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
            "name": "TRIP_Database_Guidelines_Search",
            "arguments": {"query": query, "limit": limit, "search_type": search_type},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["TRIP_Database_Guidelines_Search"]
