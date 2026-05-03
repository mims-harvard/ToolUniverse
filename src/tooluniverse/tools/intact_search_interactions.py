"""
intact_search_interactions

Search for interactions in IntAct database using EBI Search API (IntAct domain). Supports searchi...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def intact_search_interactions(
    query: str,
    first: Optional[int] = 0,
    max: Optional[int] = 25,
    format: Optional[str] = "json",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search for interactions in IntAct database using EBI Search API (IntAct domain). Supports searchi...

    Parameters
    ----------
    query : str
        Search query string (e.g., protein name, gene name, interaction type)
    first : int
        First result index for pagination (default: 0)
    max : int
        Maximum number of results to return (default: 25, max: 100)
    format : str

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
    _args = {
        k: v
        for k, v in {
            "query": query,
            "first": first,
            "max": max,
            "format": format,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "intact_search_interactions",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["intact_search_interactions"]
