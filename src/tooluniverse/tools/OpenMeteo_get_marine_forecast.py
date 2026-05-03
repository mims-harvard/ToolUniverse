"""
OpenMeteo_get_marine_forecast

Get marine/ocean weather forecast for any coastal or offshore location using Open-Meteo (free, no...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenMeteo_get_marine_forecast(
    latitude: float,
    longitude: float,
    hourly: Optional[str | Any] = None,
    daily: Optional[str | Any] = None,
    forecast_days: Optional[int | Any] = None,
    timezone: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get marine/ocean weather forecast for any coastal or offshore location using Open-Meteo (free, no...

    Parameters
    ----------
    latitude : float
        Latitude in decimal degrees (e.g., 52.0 for North Sea, 21.3 for Hawaii, -33.9...
    longitude : float
        Longitude in decimal degrees (e.g., 4.0 for North Sea, -157.8 for Hawaii, 151...
    hourly : str | Any
        Comma-separated hourly marine variables. Options: wave_height, wave_direction...
    daily : str | Any
        Comma-separated daily marine variables. Options: wave_height_max, wave_direct...
    forecast_days : int | Any
        Number of forecast days (1-16, default 7)
    timezone : str | Any
        Timezone for local time (e.g., 'Europe/London', 'Pacific/Honolulu', 'auto')
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
        for k, v in {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": hourly,
            "daily": daily,
            "forecast_days": forecast_days,
            "timezone": timezone,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OpenMeteo_get_marine_forecast",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenMeteo_get_marine_forecast"]
