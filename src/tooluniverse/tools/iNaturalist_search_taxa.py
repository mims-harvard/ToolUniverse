"""
iNaturalist_search_taxa

Search for species and taxa in the iNaturalist taxonomy. Returns matching organisms with their sc...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def iNaturalist_search_taxa(
    query: str,
    per_page: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search for species and taxa in the iNaturalist taxonomy. Returns matching organisms with their sc...

    Parameters
    ----------
    query : str
        Search query for taxon name (scientific or common). Examples: 'Panthera tigri...
    per_page : int | Any
        Number of results to return (1-200, default 10).
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
        k: v for k, v in {"query": query, "per_page": per_page}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "iNaturalist_search_taxa",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["iNaturalist_search_taxa"]
