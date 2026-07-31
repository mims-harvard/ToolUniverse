"""
LitVar_get_variant_details

Get the full structured variant record from NCBI LitVar2 by rsID (the 'variant/get' endpoint, WIT...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def LitVar_get_variant_details(
    rsid: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the full structured variant record from NCBI LitVar2 by rsID (the 'variant/get' endpoint, WIT...

    Parameters
    ----------
    rsid : str
        dbSNP rsID of the variant (e.g., 'rs113488022' = BRAF V600E, 'rs121913529' = ...
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
    _args = {k: v for k, v in {"rsid": rsid}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "LitVar_get_variant_details",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["LitVar_get_variant_details"]
