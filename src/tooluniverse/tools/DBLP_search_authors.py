"""
DBLP_search_authors

Search and disambiguate authors in the DBLP Computer Science Bibliography by name. Resolves an au...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DBLP_search_authors(
    query: str,
    limit: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search and disambiguate authors in the DBLP Computer Science Bibliography by name. Resolves an au...

    Parameters
    ----------
    query : str
        Author name to search for (e.g., 'jure leskovec', 'yann lecun', 'Geoffrey Hin...
    limit : int
        Maximum number of author hits to return (default 10, max 1000).
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
    _args = {k: v for k, v in {"query": query, "limit": limit}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "DBLP_search_authors",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DBLP_search_authors"]
