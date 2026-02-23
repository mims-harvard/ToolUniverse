"""
SunriseSunset_get_times

Get sunrise, sunset, solar noon, and twilight times for any location on Earth using the Sunrise-S...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SunriseSunset_get_times(
    lat: float,
    lng: float,
    date: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get sunrise, sunset, solar noon, and twilight times for any location on Earth using the Sunrise-S...

    Parameters
    ----------
    lat : float
        Latitude in decimal degrees (-90 to 90). Examples: 40.7128 (New York), 51.507...
    lng : float
        Longitude in decimal degrees (-180 to 180). Examples: -74.0060 (New York), -0...
    date : str | Any
        Date in YYYY-MM-DD format, or 'today'. Default: today. Examples: '2024-06-21'...
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
            "name": "SunriseSunset_get_times",
            "arguments": {"lat": lat, "lng": lng, "date": date},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SunriseSunset_get_times"]
