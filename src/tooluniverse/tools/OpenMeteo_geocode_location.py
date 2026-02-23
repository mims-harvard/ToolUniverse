"""
OpenMeteo_geocode_location

Search for city/location coordinates using Open-Meteo's free geocoding API. Returns latitude, lon...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenMeteo_geocode_location(
    name: str,
    count: Optional[int | Any] = None,
    language: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search for city/location coordinates using Open-Meteo's free geocoding API. Returns latitude, lon...

    Parameters
    ----------
    name : str
        City or location name to search (e.g., 'London', 'New York', 'Tokyo', 'Paris'...
    count : int | Any
        Number of results to return (default 10, max 100)
    language : str | Any
        Language for result names (e.g., 'en', 'de', 'fr', 'ja', 'zh'). Default 'en'.
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
            "name": "OpenMeteo_geocode_location",
            "arguments": {"name": name, "count": count, "language": language},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenMeteo_geocode_location"]
