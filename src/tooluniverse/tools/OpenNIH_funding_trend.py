"""
OpenNIH_funding_trend

Return annual NIH funding totals and project-row counts for all NIH or a selected Institute/Cente...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenNIH_funding_trend(
    fiscal_year_start: Optional[int] = None,
    fiscal_year_end: Optional[int] = None,
    ic: Optional[str] = None,
    activity_code: Optional[str] = None,
    institution: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Return annual NIH funding totals and project-row counts for all NIH or a selected Institute/Cente...

    Parameters
    ----------
    fiscal_year_start : int

    fiscal_year_end : int

    ic : str
        NIH Institute/Center filter.
    activity_code : str
        Activity code such as R01.
    institution : str
        Institution name substring.
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
            "activity_code": activity_code,
            "institution": institution,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OpenNIH_funding_trend",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenNIH_funding_trend"]
