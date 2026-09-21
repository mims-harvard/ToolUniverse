"""
OpenFDADevice_get_classification

Look up a medical device's US regulatory classification by device name. Returns device class (1 =...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenFDADevice_get_classification(
    device_name: str,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Look up a medical device's US regulatory classification by device name. Returns device class (1 =...

    Parameters
    ----------
    device_name : str
        Device type name, e.g. 'pacemaker', 'insulin pump'.
    limit : int
        Max classifications to return, 1-100. Default 20.
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
        for k, v in {"device_name": device_name, "limit": limit}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OpenFDADevice_get_classification",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenFDADevice_get_classification"]
