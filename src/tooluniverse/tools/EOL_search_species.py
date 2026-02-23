"""
EOL_search_species

Search the Encyclopedia of Life (EOL) for species and taxa by name. Returns matching EOL page IDs...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EOL_search_species(
    query: str,
    page: Optional[int] = 1,
    exact: Optional[bool] = False,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the Encyclopedia of Life (EOL) for species and taxa by name. Returns matching EOL page IDs...

    Parameters
    ----------
    query : str
        Search string for species or taxon name. Supports scientific names, common na...
    page : int
        Page number for paginated results (1-based).
    exact : bool
        If true, only return exact name matches.
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
            "name": "EOL_search_species",
            "arguments": {"query": query, "page": page, "exact": exact},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EOL_search_species"]
