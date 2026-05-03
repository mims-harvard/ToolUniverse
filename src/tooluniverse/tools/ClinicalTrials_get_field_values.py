"""
ClinicalTrials_get_field_values

Get value distribution for a specific field across ClinicalTrials.gov studies. Returns all unique...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ClinicalTrials_get_field_values(
    field: str,
    query_cond: Optional[str | Any] = None,
    page_size: Optional[int] = 50,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get value distribution for a specific field across ClinicalTrials.gov studies. Returns all unique...

    Parameters
    ----------
    field : str
        Field name to get value counts for. Common fields: 'OverallStatus' (trial sta...
    query_cond : str | Any
        Optional condition filter to restrict value counts to a specific disease area.
    page_size : int
        Number of field values to return (default 50).
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
            "field": field,
            "query_cond": query_cond,
            "page_size": page_size,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ClinicalTrials_get_field_values",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ClinicalTrials_get_field_values"]
