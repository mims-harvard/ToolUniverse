"""
OpenNIH_funding_growth

Calculate annual competitive Research Project Grant (RPG) funding growth and window CAGR for all ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenNIH_funding_growth(
    entity_id: Optional[str] = None,
    fiscal_year_start: Optional[int] = None,
    fiscal_year_end: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Calculate annual competitive Research Project Grant (RPG) funding growth and window CAGR for all ...

    Parameters
    ----------
    entity_id : str
        Canonical institution identifier or null for all NIH.
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
            "entity_id": entity_id,
            "fiscal_year_start": fiscal_year_start,
            "fiscal_year_end": fiscal_year_end,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OpenNIH_funding_growth",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenNIH_funding_growth"]
