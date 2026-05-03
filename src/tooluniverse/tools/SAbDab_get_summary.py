"""
SAbDab_get_summary

Get SAbDab database summary and statistics. Returns information about database content, features,...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SAbDab_get_summary(
    operation: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get SAbDab database summary and statistics. Returns information about database content, features,...

    Parameters
    ----------
    operation : str

    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {"operation": operation}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "SAbDab_get_summary",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SAbDab_get_summary"]
