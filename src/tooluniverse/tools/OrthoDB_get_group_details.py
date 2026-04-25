"""
OrthoDB_get_group_details

Get detailed information about an OrthoDB orthologous group including functional annotations. Ret...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OrthoDB_get_group_details(
    group_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed information about an OrthoDB orthologous group including functional annotations. Ret...

    Parameters
    ----------
    group_id : str
        OrthoDB group ID. Format: 'numberATtaxid'. Examples: '727649at7742' (Vertebra...
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
        "group_id": group_id
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "OrthoDB_get_group_details",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["OrthoDB_get_group_details"]
