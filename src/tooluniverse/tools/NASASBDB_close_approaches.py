"""
NASASBDB_close_approaches

Query NASA's Close Approach Data (CAD) API for asteroids and comets making close approaches to Ea...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NASASBDB_close_approaches(
    dist_max: Optional[str | Any] = None,
    date_min: Optional[str | Any] = None,
    date_max: Optional[str | Any] = None,
    h_max: Optional[float | Any] = None,
    des: Optional[str | Any] = None,
    limit: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Query NASA's Close Approach Data (CAD) API for asteroids and comets making close approaches to Ea...

    Parameters
    ----------
    dist_max : str | Any
        Maximum approach distance in AU. Examples: '0.01' (1.5 million km), '0.05' (7...
    date_min : str | Any
        Start date for search (YYYY-MM-DD format). Default: current date.
    date_max : str | Any
        End date for search (YYYY-MM-DD format). Example: '2025-12-31'
    h_max : float | Any
        Filter by maximum absolute magnitude H (smaller H = larger object). H<18 is ~...
    des : str | Any
        Filter by specific body designation (e.g., '99942' for Apophis, '2020 SO')
    limit : int | Any
        Maximum number of results (default 50, max 10000)
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
            "name": "NASASBDB_close_approaches",
            "arguments": {
                "dist-max": dist_max,
                "date-min": date_min,
                "date-max": date_max,
                "h-max": h_max,
                "des": des,
                "limit": limit,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NASASBDB_close_approaches"]
