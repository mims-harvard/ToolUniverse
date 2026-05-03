"""
FDA_OrangeBook_get_patent_info

Get patent information for approved drugs. Note: Full patent details (numbers, expiration dates) ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FDA_OrangeBook_get_patent_info(
    operation: Optional[str] = None,
    application_number: Optional[str] = None,
    brand_name: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get patent information for approved drugs. Note: Full patent details (numbers, expiration dates) ...

    Parameters
    ----------
    operation : str
        Operation type (fixed)
    application_number : str
        FDA application number
    brand_name : str
        Brand name of drug
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
            "application_number": application_number,
            "brand_name": brand_name,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "FDA_OrangeBook_get_patent_info",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FDA_OrangeBook_get_patent_info"]
