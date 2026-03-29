"""
COD_get_structure

Get detailed crystal structure information from the Crystallography Open Database (COD) by COD en...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def COD_get_structure(
    cod_id: Optional[str] = None,
    id: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed crystal structure information from the Crystallography Open Database (COD) by COD en...

    Parameters
    ----------
    cod_id : str
        Alias for 'id'. COD structure entry ID (numeric string). Examples: '9008460' ...
    id : str
        COD structure entry ID (numeric string). Examples: '9008460' (Aluminum), '101...
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
    _args = {k: v for k, v in {"cod_id": cod_id, "id": id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "COD_get_structure",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["COD_get_structure"]
