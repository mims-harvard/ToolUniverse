"""
FAERS_count_drug_routes_by_event

Count the most common routes of administration for drugs involved in adverse event reports. Only ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FAERS_count_drug_routes_by_event(
    medicinalproduct: str,
    serious: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Count the most common routes of administration for drugs involved in adverse event reports. Only ...

    Parameters
    ----------
    medicinalproduct : str
        Drug name.
    serious : str
        Optional: Filter by event seriousness. Omit this parameter if you don't want ...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {"medicinalproduct": medicinalproduct, "serious": serious}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "FAERS_count_drug_routes_by_event",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FAERS_count_drug_routes_by_event"]
