"""
ProtacDB_get_protac

Get detailed information about a specific PROTAC compound by its PROTAC-DB ID. Returns full recor...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ProtacDB_get_protac(
    operation: str,
    protac_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed information about a specific PROTAC compound by its PROTAC-DB ID. Returns full recor...

    Parameters
    ----------
    operation : str
        Operation type
    protac_id : str
        PROTAC-DB compound ID (e.g., '1', '42', '100')
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
        for k, v in {"operation": operation, "protac_id": protac_id}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ProtacDB_get_protac",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ProtacDB_get_protac"]
