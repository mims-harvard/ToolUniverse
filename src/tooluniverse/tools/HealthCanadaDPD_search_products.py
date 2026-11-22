"""
HealthCanadaDPD_search_products

Search the Health Canada Drug Product Database (DPD), the register of every drug product authoriz...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def HealthCanadaDPD_search_products(
    brand_name: Optional[str] = None,
    din: Optional[str] = None,
    marketed_only: Optional[bool] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any] | dict[str, Any]:
    """
    Search the Health Canada Drug Product Database (DPD), the register of every drug product authoriz...

    Parameters
    ----------
    brand_name : str
        Brand name or part of it, e.g. 'gleevec'. Give this or din.
    din : str
        Drug Identification Number, up to 8 digits, e.g. '02253275'.
    marketed_only : bool
        Keep only products with status Marketed (default false: all statuses).
    limit : int
        Products to return (default 25, at most 100).
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any] | dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "brand_name": brand_name,
            "din": din,
            "marketed_only": marketed_only,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "HealthCanadaDPD_search_products",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["HealthCanadaDPD_search_products"]
