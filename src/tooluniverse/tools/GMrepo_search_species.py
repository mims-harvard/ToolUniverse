"""
GMrepo_search_species

Search the GMrepo database for gut microbiome species by name. Returns species with NCBI taxon ID...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GMrepo_search_species(
    query: str,
    limit: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search the GMrepo database for gut microbiome species by name. Returns species with NCBI taxon ID...

    Parameters
    ----------
    query : str
        Species name or partial name to search. Examples: 'Akkermansia', 'Bacteroides...
    limit : int
        Maximum number of results to return. Default: 20.
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
    _args = {k: v for k, v in {"query": query, "limit": limit}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "GMrepo_search_species",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GMrepo_search_species"]
