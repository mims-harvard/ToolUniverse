"""
FDAGSRS_get_substance

Get full FDA substance record by UNII (Unique Ingredient Identifier) code. Returns complete subst...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FDAGSRS_get_substance(
    unii: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get full FDA substance record by UNII (Unique Ingredient Identifier) code. Returns complete subst...

    Parameters
    ----------
    unii : str
        FDA UNII (Unique Ingredient Identifier) code. 10-character alphanumeric strin...
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
    _args = {k: v for k, v in {"unii": unii}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "FDAGSRS_get_substance",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FDAGSRS_get_substance"]
