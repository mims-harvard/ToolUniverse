"""
OpenMeteo_get_flood_forecast

Get river discharge and flood forecast data for any location using Open-Meteo's free GloFAS (Glob...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenMeteo_get_flood_forecast(
    latitude: float,
    longitude: float,
    daily: Optional[str | Any] = None,
    forecast_days: Optional[int | Any] = None,
    past_days: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get river discharge and flood forecast data for any location using Open-Meteo's free GloFAS (Glob...

    Parameters
    ----------
    latitude : float
        Latitude in decimal degrees (e.g., 52.52 for Berlin, 48.85 for Paris, 29.76 f...
    longitude : float
        Longitude in decimal degrees (e.g., 13.41 for Berlin, 2.35 for Paris, -95.37 ...
    daily : str | Any
        Comma-separated daily variables. Options: river_discharge, river_discharge_me...
    forecast_days : int | Any
        Number of forecast days (1-210, default 92). GloFAS provides seasonal forecas...
    past_days : int | Any
        Number of past days to include (0-92, default 0). Includes recent historical ...
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
    _args = {k: v for k, v in {
        "latitude": latitude,
                "longitude": longitude,
                "daily": daily,
                "forecast_days": forecast_days,
                "past_days": past_days
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "OpenMeteo_get_flood_forecast",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["OpenMeteo_get_flood_forecast"]
