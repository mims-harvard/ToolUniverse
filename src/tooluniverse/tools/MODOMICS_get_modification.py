"""
MODOMICS_get_modification

Get detailed information about a specific RNA modification from MODOMICS by its numeric ID. Retur...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MODOMICS_get_modification(
    modification_id: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed information about a specific RNA modification from MODOMICS by its numeric ID. Retur...

    Parameters
    ----------
    modification_id : int
        MODOMICS modification numeric ID. Examples: 78 (pseudouridine), 2 (5,2'-O-dim...
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
        k: v for k, v in {"modification_id": modification_id}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MODOMICS_get_modification",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MODOMICS_get_modification"]
