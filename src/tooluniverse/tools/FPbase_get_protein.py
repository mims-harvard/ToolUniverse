"""
FPbase_get_protein

Get detailed data for a fluorescent protein from FPbase by its slug/short name. Returns the prote...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FPbase_get_protein(
    slug: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed data for a fluorescent protein from FPbase by its slug/short name. Returns the prote...

    Parameters
    ----------
    slug : str
        Fluorescent protein slug/short name in lowercase (e.g., 'egfp', 'mcherry', 't...
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
    _args = {k: v for k, v in {
        "slug": slug
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "FPbase_get_protein",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["FPbase_get_protein"]
