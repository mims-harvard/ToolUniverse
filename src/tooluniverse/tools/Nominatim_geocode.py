"""
Nominatim_geocode

Geocode addresses and place names to geographic coordinates using the OpenStreetMap Nominatim ser...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Nominatim_geocode(
    q: str,
    limit: Optional[int | Any] = None,
    countrycodes: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Geocode addresses and place names to geographic coordinates using the OpenStreetMap Nominatim ser...

    Parameters
    ----------
    q : str
        Free-form address or place name query. Examples: 'Eiffel Tower Paris', '1600 ...
    limit : int | Any
        Maximum number of results to return (default 5, max 50)
    countrycodes : str | Any
        Restrict to specific countries (comma-separated ISO 3166-1 alpha-2 codes). Ex...
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
            "name": "Nominatim_geocode",
            "arguments": {"q": q, "limit": limit, "countrycodes": countrycodes},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Nominatim_geocode"]
