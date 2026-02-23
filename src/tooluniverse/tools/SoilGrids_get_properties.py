"""
SoilGrids_get_properties

Get soil properties for any location on Earth using the ISRIC SoilGrids API. Returns quantitative...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SoilGrids_get_properties(
    lon: float,
    lat: float,
    property: Optional[str | Any] = None,
    depth: Optional[str | Any] = None,
    value: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get soil properties for any location on Earth using the ISRIC SoilGrids API. Returns quantitative...

    Parameters
    ----------
    lon : float
        Longitude in decimal degrees (-180 to 180). Examples: 5.1 (Netherlands), -122...
    lat : float
        Latitude in decimal degrees (-90 to 90). Examples: 52.1 (Netherlands), 37.8 (...
    property : str | Any
        Soil property to retrieve. Multiple allowed (repeat param). Properties: 'bdod...
    depth : str | Any
        Soil depth interval. Values: '0-5cm', '5-15cm', '15-30cm', '30-60cm', '60-100...
    value : str | Any
        Statistical value to return. Values: 'mean' (default), 'Q0.05' (5th percentil...
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
            "name": "SoilGrids_get_properties",
            "arguments": {
                "lon": lon,
                "lat": lat,
                "property": property,
                "depth": depth,
                "value": value,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SoilGrids_get_properties"]
