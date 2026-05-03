"""
FDA_OrangeBook_get_te_code

Get therapeutic equivalence (TE) codes for drug products. AB=bioequivalent/substitutable, AT=topi...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FDA_OrangeBook_get_te_code(
    operation: Optional[str] = None,
    brand_name: Optional[str] = None,
    generic_name: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get therapeutic equivalence (TE) codes for drug products. AB=bioequivalent/substitutable, AT=topi...

    Parameters
    ----------
    operation : str
        Operation type (fixed)
    brand_name : str
        Brand name to check TE codes
    generic_name : str
        Generic name to check TE codes
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
            "name": "FDA_OrangeBook_get_te_code",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FDA_OrangeBook_get_te_code"]
