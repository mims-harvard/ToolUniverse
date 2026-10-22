"""
TheraSAbDab_get_all_therapeutics

Get the complete Thera-SAbDab therapeutic-antibody catalog through limit/offset pages, plus count...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def TheraSAbDab_get_all_therapeutics(
    limit: Optional[int] = 100,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get the complete Thera-SAbDab therapeutic-antibody catalog through limit/offset pages, plus count...

    Parameters
    ----------
    limit : int
        Maximum catalog records to return
    offset : int
        Zero-based catalog offset; continue with next_offset
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
        k: v for k, v in {"limit": limit, "offset": offset}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "TheraSAbDab_get_all_therapeutics",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["TheraSAbDab_get_all_therapeutics"]
