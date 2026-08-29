"""
OpenNIH_get_pi_profile

Publications are not returned by the deployed endpoint. Return PI grant rows and shared-award con...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenNIH_get_pi_profile(
    profile_id: str,
    fiscal_year_start: Optional[int] = None,
    fiscal_year_end: Optional[int] = None,
    limit: Optional[int] = 20,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Publications are not returned by the deployed endpoint. Return PI grant rows and shared-award con...

    Parameters
    ----------
    profile_id : str
        NIH RePORTER PI profile identifier from a search result.
    fiscal_year_start : int

    fiscal_year_end : int

    limit : int

    offset : int

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
            "profile_id": profile_id,
            "fiscal_year_start": fiscal_year_start,
            "fiscal_year_end": fiscal_year_end,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OpenNIH_get_pi_profile",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenNIH_get_pi_profile"]
