"""
OpenNIH_activity_code_distribution

Break NIH or one Institute/Center portfolio into research, career, training, center, contract, in...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenNIH_activity_code_distribution(
    fiscal_year_start: Optional[int] = None,
    fiscal_year_end: Optional[int] = None,
    ic: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Break NIH or one Institute/Center portfolio into research, career, training, center, contract, in...

    Parameters
    ----------
    fiscal_year_start : int

    fiscal_year_end : int

    ic : str
        NIH Institute/Center filter.
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
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OpenNIH_activity_code_distribution",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenNIH_activity_code_distribution"]
