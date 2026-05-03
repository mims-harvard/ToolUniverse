"""
OpenMeteo_get_weather_forecast

Get current weather and forecasts for any location using Open-Meteo (free, no API key needed). Re...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenMeteo_get_weather_forecast(
    latitude: float,
    longitude: float,
    current: Optional[str | Any] = None,
    daily: Optional[str | Any] = None,
    hourly: Optional[str | Any] = None,
    forecast_days: Optional[int | Any] = None,
    timezone: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get current weather and forecasts for any location using Open-Meteo (free, no API key needed). Re...

    Parameters
    ----------
    latitude : float
        Latitude in decimal degrees (e.g., 51.5 for London, 40.7 for New York, 35.7 f...
    longitude : float
        Longitude in decimal degrees (e.g., -0.12 for London, -74.0 for New York, 139...
    current : str | Any
        Comma-separated current weather variables (e.g., 'temperature_2m,wind_speed_1...
    daily : str | Any
        Comma-separated daily forecast variables (e.g., 'temperature_2m_max,temperatu...
    hourly : str | Any
        Comma-separated hourly variables (e.g., 'temperature_2m,precipitation_probabi...
    forecast_days : int | Any
        Number of forecast days (1-16, default 7)
    timezone : str | Any
        Timezone for local time (e.g., 'Europe/London', 'America/New_York', 'Asia/Tok...
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
            "current": current,
            "daily": daily,
            "hourly": hourly,
            "forecast_days": forecast_days,
            "timezone": timezone,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OpenMeteo_get_weather_forecast",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenMeteo_get_weather_forecast"]
