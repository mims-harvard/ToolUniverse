"""
ChEMBL_get_activity

Get detailed information about a specific activity by its activity ID. Activity IDs are found in ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ChEMBL_get_activity(
    activity_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed information about a specific activity by its activity ID. Activity IDs are found in ...

    Parameters
    ----------
    activity_id : str
        ChEMBL activity ID
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
    _args = {k: v for k, v in {"activity_id": activity_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ChEMBL_get_activity",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ChEMBL_get_activity"]
