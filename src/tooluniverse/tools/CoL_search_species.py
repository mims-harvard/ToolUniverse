"""
CoL_search_species

Search the Catalogue of Life (CoL) for species and other taxa by scientific name. CoL is the glob...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CoL_search_species(
    q: str,
    rank: Optional[str | Any] = None,
    limit: Optional[int | Any] = None,
    offset: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the Catalogue of Life (CoL) for species and other taxa by scientific name. CoL is the glob...

    Parameters
    ----------
    q : str
        Scientific name to search for (e.g., 'Homo sapiens', 'Panthera leo', 'Arabido...
    rank : str | Any
        Filter by taxonomic rank: 'species', 'genus', 'family', 'order', 'class', 'ph...
    limit : int | Any
        Maximum number of results to return (default 10, max 1000)
    offset : int | Any
        Offset for pagination
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
        for k, v in {"q": q, "rank": rank, "limit": limit, "offset": offset}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "CoL_search_species",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CoL_search_species"]
