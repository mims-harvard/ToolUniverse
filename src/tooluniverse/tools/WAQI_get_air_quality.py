"""
WAQI_get_air_quality

Get real-time Air Quality Index (AQI) data for a city or monitoring station using the World Air Q...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def WAQI_get_air_quality(
    city: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get real-time Air Quality Index (AQI) data for a city or monitoring station using the World Air Q...

    Parameters
    ----------
    city : str
        City name or station name to get AQI for. Examples: 'beijing', 'london', 'new...
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
        {"name": "WAQI_get_air_quality", "arguments": {"city": city}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["WAQI_get_air_quality"]
