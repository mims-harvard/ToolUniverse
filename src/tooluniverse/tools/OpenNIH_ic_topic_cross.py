"""
OpenNIH_ic_topic_cross

Measure one research topic within one NIH Institute/Center (IC), or within one combined all-IC sc...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenNIH_ic_topic_cross(
    ic: str,
    query: str,
    fiscal_year_start: Optional[int] = None,
    fiscal_year_end: Optional[int] = None,
    match_strategy: Optional[str] = "auto",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Measure one research topic within one NIH Institute/Center (IC), or within one combined all-IC sc...

    Parameters
    ----------
    ic : str
        One Institute/Center abbreviation, code, or name; use ALL for one combined al...
    query : str
        Research topic or RCDC category.
    fiscal_year_start : int

    fiscal_year_end : int

    match_strategy : str

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
            "ic": ic,
            "query": query,
            "fiscal_year_start": fiscal_year_start,
            "fiscal_year_end": fiscal_year_end,
            "match_strategy": match_strategy,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OpenNIH_ic_topic_cross",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenNIH_ic_topic_cross"]
