"""
Nominatim_reverse_geocode

Reverse geocode latitude/longitude coordinates to a human-readable address using OpenStreetMap No...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Nominatim_reverse_geocode(
    lat: float,
    lon: float,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Reverse geocode latitude/longitude coordinates to a human-readable address using OpenStreetMap No...

    Parameters
    ----------
    lat : float
        Latitude in decimal degrees. Examples: 48.8582 (Paris), 51.5007 (London), 40....
    lon : float
        Longitude in decimal degrees. Examples: 2.2945 (Paris), -0.1246 (London), -73...
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
        {"name": "Nominatim_reverse_geocode", "arguments": {"lat": lat, "lon": lon}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Nominatim_reverse_geocode"]
