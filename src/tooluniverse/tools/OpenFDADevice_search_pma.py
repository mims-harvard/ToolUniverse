"""
OpenFDADevice_search_pma

Search openFDA's Premarket Approval (PMA) database by trade name -- the pathway required for high...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenFDADevice_search_pma(
    device_name: str,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search openFDA's Premarket Approval (PMA) database by trade name -- the pathway required for high...

    Parameters
    ----------
    device_name : str
        Device trade name, e.g. 'pacemaker', 'defibrillator'.
    limit : int
        Max PMA records to return, 1-100. Default 20.
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
            "name": "OpenFDADevice_search_pma",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenFDADevice_search_pma"]
