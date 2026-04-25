"""
IDR_get_study

Get detailed information about a specific imaging study (project) in the Image Data Resource (IDR...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def IDR_get_study(
    project_id: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed information about a specific imaging study (project) in the Image Data Resource (IDR...

    Parameters
    ----------
    project_id : int
        IDR project/study ID (e.g., 101 for idr0018-neff-histopathology). Obtain from...
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
        "project_id": project_id
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "IDR_get_study",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["IDR_get_study"]
