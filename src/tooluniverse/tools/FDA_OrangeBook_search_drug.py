"""
FDA_OrangeBook_search_drug

Search FDA Drugs@FDA database by brand name, generic name, or application number. Returns approva...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FDA_OrangeBook_search_drug(
    operation: Optional[str] = None,
    brand_name: Optional[str] = None,
    generic_name: Optional[str] = None,
    application_number: Optional[str] = None,
    limit: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search FDA Drugs@FDA database by brand name, generic name, or application number. Returns approva...

    Parameters
    ----------
    operation : str
        Operation type (fixed)
    brand_name : str
        Brand/trade name of drug (e.g., 'ADVIL', 'LIPITOR')
    generic_name : str
        Generic/active ingredient name (e.g., 'IBUPROFEN', 'ATORVASTATIN')
    application_number : str
        FDA application number (e.g., 'NDA020402', 'ANDA078394')
    limit : int
        Maximum number of results (1-100, default 10)
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
            "application_number": application_number,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "FDA_OrangeBook_search_drug",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FDA_OrangeBook_search_drug"]
