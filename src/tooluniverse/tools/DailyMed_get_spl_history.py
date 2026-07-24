"""
DailyMed_get_spl_history

Get the full version history of a DailyMed SPL Set ID: every published SPL version with its versi...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DailyMed_get_spl_history(
    setid: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the full version history of a DailyMed SPL Set ID: every published SPL version with its versi...

    Parameters
    ----------
    setid : str
        DailyMed SPL Set ID UUID. Example: '43c94480-78d1-4a23-91d4-1d49fea72cb7'.
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
    _args = {k: v for k, v in {"setid": setid}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "DailyMed_get_spl_history",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DailyMed_get_spl_history"]
