"""
OpenMeteo_get_air_quality

Get current and forecast air quality data for any location using the Open-Meteo Air Quality API. ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenMeteo_get_air_quality(
    latitude: float,
    longitude: float,
    hourly: Optional[str | Any] = None,
    forecast_days: Optional[int | Any] = None,
    past_days: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get current and forecast air quality data for any location using the Open-Meteo Air Quality API. ...

    Parameters
    ----------
    latitude : float
        Location latitude (-90 to 90). Examples: 52.52 (Berlin), 40.71 (NYC), 48.85 (...
    longitude : float
        Location longitude (-180 to 180). Examples: 13.41 (Berlin), -74.01 (NYC), 2.3...
    hourly : str | Any
        Comma-separated air quality variables. Values: 'pm10', 'pm2_5', 'carbon_monox...
    forecast_days : int | Any
        Number of forecast days (1-7). Default: 5
    past_days : int | Any
        Include past days in response (0-92). Examples: 1, 7
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
            "forecast_days": forecast_days,
            "past_days": past_days,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OpenMeteo_get_air_quality",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenMeteo_get_air_quality"]
