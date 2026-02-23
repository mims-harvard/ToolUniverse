"""
POWO_search_plants

Search the Plants of the World Online (POWO) database maintained by the Royal Botanic Gardens, Ke...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def POWO_search_plants(
    q: str,
    f: Optional[str | Any] = None,
    perPage: Optional[int | Any] = None,
    cursor: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the Plants of the World Online (POWO) database maintained by the Royal Botanic Gardens, Ke...

    Parameters
    ----------
    q : str
        Search query. Can be scientific name, common name, genus, or family. Examples...
    f : str | Any
        Filter facets (comma-separated). Common filters: 'species_f:true' (species on...
    perPage : int | Any
        Results per page (default 24, max 500)
    cursor : str | Any
        Pagination cursor from previous response
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
            "name": "POWO_search_plants",
            "arguments": {"q": q, "f": f, "perPage": perPage, "cursor": cursor},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["POWO_search_plants"]
