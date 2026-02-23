"""
OpenMeteo_get_air_quality

Get current and forecasted air quality data for any location using Open-Meteo's free air quality ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenMeteo_get_air_quality(
    latitude: float,
    longitude: float,
    current: Optional[str | Any] = None,
    hourly: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get current and forecasted air quality data for any location using Open-Meteo's free air quality ...

    Parameters
    ----------
    latitude : float
        Latitude in decimal degrees (e.g., 51.5 for London, 40.7 for New York)
    longitude : float
        Longitude in decimal degrees (e.g., -0.12 for London, -74.0 for New York)
    current : str | Any
        Comma-separated current variables (e.g., 'pm10,pm2_5,carbon_monoxide,nitrogen...
    hourly : str | Any
        Comma-separated hourly variables (e.g., 'pm10,pm2_5,ozone,nitrogen_dioxide,eu...
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
            "name": "OpenMeteo_get_air_quality",
            "arguments": {
                "latitude": latitude,
                "longitude": longitude,
                "current": current,
                "hourly": hourly,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenMeteo_get_air_quality"]
