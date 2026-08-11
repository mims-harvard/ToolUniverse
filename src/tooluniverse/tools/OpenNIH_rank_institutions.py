"""
OpenNIH_rank_institutions

Rank institutions within competitive Research Project Grant (RPG) research and return entity IDs ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenNIH_rank_institutions(
    fiscal_year_start: Optional[int] = None,
    fiscal_year_end: Optional[int] = None,
    ic: Optional[str] = None,
    sort_by: Optional[str] = "composite",
    limit: Optional[int] = 20,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Rank institutions within competitive Research Project Grant (RPG) research and return entity IDs ...

    Parameters
    ----------
    fiscal_year_start : int

    fiscal_year_end : int

    ic : str

    sort_by : str
        Ranking objective. Use funding_scale for 'top-funded'; composite is a weighte...
    limit : int

    offset : int

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
    _args = {
        k: v
        for k, v in {
            "fiscal_year_start": fiscal_year_start,
            "fiscal_year_end": fiscal_year_end,
            "ic": ic,
            "sort_by": sort_by,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OpenNIH_rank_institutions",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenNIH_rank_institutions"]
