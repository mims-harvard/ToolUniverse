"""
OpenNIH_topic_trend

Trace annual NIH project-row counts and recorded award totals for a research topic using title-ke...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenNIH_topic_trend(
    query: str,
    fiscal_year_start: Optional[int] = None,
    fiscal_year_end: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Trace annual NIH project-row counts and recorded award totals for a research topic using title-ke...

    Parameters
    ----------
    query : str
        Topic words to match in grant titles.
    fiscal_year_start : int

    fiscal_year_end : int

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
            "query": query,
            "fiscal_year_start": fiscal_year_start,
            "fiscal_year_end": fiscal_year_end,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OpenNIH_topic_trend",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenNIH_topic_trend"]
