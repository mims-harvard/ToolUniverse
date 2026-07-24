"""
FooDB_get_compound

Get a food constituent/chemical from FooDB (the largest food-chemical database) by its FooDB comp...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FooDB_get_compound(
    fdb_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get a food constituent/chemical from FooDB (the largest food-chemical database) by its FooDB comp...

    Parameters
    ----------
    fdb_id : str
        FooDB compound id, e.g. 'FDB000004'.
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
    _args = {k: v for k, v in {"fdb_id": fdb_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "FooDB_get_compound",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FooDB_get_compound"]
