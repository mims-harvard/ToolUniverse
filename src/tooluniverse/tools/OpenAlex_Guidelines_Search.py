"""
OpenAlex_Guidelines_Search

Search for clinical practice guidelines using OpenAlex scholarly database. Provides access to a c...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenAlex_Guidelines_Search(
    query: str,
    limit: int,
    year_from: Optional[int | Any] = None,
    year_to: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search for clinical practice guidelines using OpenAlex scholarly database. Provides access to a c...

    Parameters
    ----------
    query : str
        Medical condition or clinical topic to search for guidelines (e.g., 'diabetes...
    limit : int
        Maximum number of guidelines to return (default: 10)
    year_from : int | Any
        Filter for guidelines published from this year onwards (optional) (optional, ...
    year_to : int | Any
        Filter for guidelines published up to this year (optional) (optional, default...
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
            "name": "OpenAlex_Guidelines_Search",
            "arguments": {
                "query": query,
                "limit": limit,
                "year_from": year_from,
                "year_to": year_to,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenAlex_Guidelines_Search"]
