"""
FDA_OrangeBook_check_generic_availability

Check if generic versions are FDA-approved for a brand-name drug. Returns reference drug info, ap...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FDA_OrangeBook_check_generic_availability(
    operation: Optional[str] = None,
    brand_name: Optional[str] = None,
    generic_name: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Check if generic versions are FDA-approved for a brand-name drug. Returns reference drug info, ap...

    Parameters
    ----------
    operation : str
        Operation type (fixed)
    brand_name : str
        Brand name to check for generics
    generic_name : str
        Generic name to check
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
        k: v
        for k, v in {
            "operation": operation,
            "brand_name": brand_name,
            "generic_name": generic_name,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "FDA_OrangeBook_check_generic_availability",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FDA_OrangeBook_check_generic_availability"]
