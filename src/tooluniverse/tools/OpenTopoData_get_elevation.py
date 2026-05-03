"""
OpenTopoData_get_elevation

Get terrain elevation data for any location on Earth using the OpenTopoData API. Returns elevatio...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenTopoData_get_elevation(
    locations: str,
    dataset: Optional[str | Any] = None,
    interpolation: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get terrain elevation data for any location on Earth using the OpenTopoData API. Returns elevatio...

    Parameters
    ----------
    locations : str
        One or more lat,lng coordinate pairs separated by | (pipe). Examples: '36.455...
    dataset : str | Any
        Elevation dataset to use. Values: 'srtm30m' (global 30m), 'srtm90m' (global 9...
    interpolation : str | Any
        Interpolation method. Values: 'nearest', 'bilinear', 'cubic'. Default: bilinear
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
            "locations": locations,
            "dataset": dataset,
            "interpolation": interpolation,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OpenTopoData_get_elevation",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenTopoData_get_elevation"]
