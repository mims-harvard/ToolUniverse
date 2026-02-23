"""
OpenMeteo_get_historical_weather

Get historical weather data for any location from Open-Meteo ERA5 reanalysis archive (1940-presen...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenMeteo_get_historical_weather(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    daily: Optional[str | Any] = None,
    hourly: Optional[str | Any] = None,
    timezone: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get historical weather data for any location from Open-Meteo ERA5 reanalysis archive (1940-presen...

    Parameters
    ----------
    latitude : float
        Latitude in decimal degrees (e.g., 51.5 for London, 40.7 for New York)
    longitude : float
        Longitude in decimal degrees (e.g., -0.12 for London, -74.0 for New York)
    start_date : str
        Start date in YYYY-MM-DD format (e.g., '2023-01-01'). Data available from 194...
    end_date : str
        End date in YYYY-MM-DD format (e.g., '2023-12-31'). Maximum range: a few mont...
    daily : str | Any
        Comma-separated daily variables (e.g., 'temperature_2m_max,temperature_2m_min...
    hourly : str | Any
        Comma-separated hourly variables (e.g., 'temperature_2m,precipitation,wind_sp...
    timezone : str | Any
        Timezone (e.g., 'Europe/London', 'America/New_York', 'auto')
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
            "name": "OpenMeteo_get_historical_weather",
            "arguments": {
                "latitude": latitude,
                "longitude": longitude,
                "start_date": start_date,
                "end_date": end_date,
                "daily": daily,
                "hourly": hourly,
                "timezone": timezone,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenMeteo_get_historical_weather"]
