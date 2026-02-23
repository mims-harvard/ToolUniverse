"""
MarineRegions_get_record

Get detailed information about a specific marine geographic feature by its MRGID (Marine Regions ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MarineRegions_get_record(
    mrgid: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed information about a specific marine geographic feature by its MRGID (Marine Regions ...

    Parameters
    ----------
    mrgid : int
        Marine Regions Gazetteer ID. Examples: 2350 (North Sea), 1901 (Pacific Ocean)...
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
        {"name": "MarineRegions_get_record", "arguments": {"mrgid": mrgid}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MarineRegions_get_record"]
