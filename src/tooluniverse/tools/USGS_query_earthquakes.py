"""
USGS_query_earthquakes

Query the USGS FDSN earthquake database with custom parameters to search historical and recent se...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def USGS_query_earthquakes(
    minmagnitude: Optional[float] = None,
    maxmagnitude: Optional[float] = None,
    starttime: Optional[str] = None,
    endtime: Optional[str] = None,
    minlatitude: Optional[float] = None,
    maxlatitude: Optional[float] = None,
    minlongitude: Optional[float] = None,
    maxlongitude: Optional[float] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Query the USGS FDSN earthquake database with custom parameters to search historical and recent se...

    Parameters
    ----------
    minmagnitude : float
        Minimum earthquake magnitude (e.g., 5.0, 6.5, 7.0)
    maxmagnitude : float
        Maximum earthquake magnitude
    starttime : str
        Start time in ISO 8601 format (e.g., '2024-01-01', '2020-01-01T00:00:00')
    endtime : str
        End time in ISO 8601 format (e.g., '2024-12-31'). Defaults to current time.
    minlatitude : float
        Minimum latitude for bounding box search (-90 to 90)
    maxlatitude : float
        Maximum latitude for bounding box search
    minlongitude : float
        Minimum longitude (-180 to 360)
    maxlongitude : float
        Maximum longitude
    limit : int
        Maximum number of events (default 20000, max 20000)
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
            "minmagnitude": minmagnitude,
            "maxmagnitude": maxmagnitude,
            "starttime": starttime,
            "endtime": endtime,
            "minlatitude": minlatitude,
            "maxlatitude": maxlatitude,
            "minlongitude": minlongitude,
            "maxlongitude": maxlongitude,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "USGS_query_earthquakes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["USGS_query_earthquakes"]
