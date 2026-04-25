"""
OpenMeteo_get_historical_climate

Get historical daily climate data for any location on Earth using the Open-Meteo Climate Change A...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenMeteo_get_historical_climate(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    daily: Optional[str | Any] = None,
    models: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get historical daily climate data for any location on Earth using the Open-Meteo Climate Change A...

    Parameters
    ----------
    latitude : float
        Location latitude (-90 to 90). Examples: 52.52 (Berlin), 40.71 (NYC), 48.85 (...
    longitude : float
        Location longitude (-180 to 180). Examples: 13.41 (Berlin), -74.01 (NYC), 2.3...
    start_date : str
        Start date in YYYY-MM-DD format. Data available from 1950-01-01. Examples: '1...
    end_date : str
        End date in YYYY-MM-DD format. Examples: '1980-12-31', '2000-06-30', '2023-12...
    daily : str | Any
        Comma-separated daily variables. Values: 'temperature_2m_mean', 'temperature_...
    models : str | Any
        Climate model. Values: 'EC_Earth3P_HR' (Europe, high res), 'MPI_ESM1_2_XR', '...
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
                "start_date": start_date,
                "end_date": end_date,
                "daily": daily,
                "models": models
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "OpenMeteo_get_historical_climate",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["OpenMeteo_get_historical_climate"]
