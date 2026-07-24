"""
CryoET_list_tiltseries

List tilt-series RAW ACQUISITION metadata from the CZ BioHub CryoET Data Portal. A tilt-series is...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CryoET_list_tiltseries(
    operation: str,
    run_id: Optional[int] = None,
    limit: Optional[int] = 10,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List tilt-series RAW ACQUISITION metadata from the CZ BioHub CryoET Data Portal. A tilt-series is...

    Parameters
    ----------
    operation : str
        Operation type
    run_id : int
        Optional: filter to tilt-series of a single run (e.g. 8260). Obtain from Cryo...
    limit : int
        Maximum number of tilt-series to return (default: 10).
    offset : int
        Number of tilt-series to skip for pagination (default: 0).
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
            "operation": operation,
            "run_id": run_id,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "CryoET_list_tiltseries",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CryoET_list_tiltseries"]
