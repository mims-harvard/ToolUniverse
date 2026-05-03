"""
civic_get_variant

Get detailed information about a specific variant in CIViC database by variant ID. Variants repre...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def civic_get_variant(
    variant_id: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed information about a specific variant in CIViC database by variant ID. Variants repre...

    Parameters
    ----------
    variant_id : int
        CIViC variant ID (e.g., 4170)
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
    _args = {k: v for k, v in {"variant_id": variant_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "civic_get_variant",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["civic_get_variant"]
