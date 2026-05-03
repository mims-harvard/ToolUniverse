"""
DailyMed_get_spl_by_setid

Get complete label corresponding to SPL Set ID, returns content in XML or JSON format.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DailyMed_get_spl_by_setid(
    setid: str,
    format: Optional[str] = "xml",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get complete label corresponding to SPL Set ID, returns content in XML or JSON format.

    Parameters
    ----------
    setid : str
        SPL Set ID to query.
    format : str
        Return format, only supports 'xml'.
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
    _args = {
        k: v for k, v in {"setid": setid, "format": format}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "DailyMed_get_spl_by_setid",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DailyMed_get_spl_by_setid"]
