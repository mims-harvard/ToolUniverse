"""
WHOGHO_get_indicator_data

Get actual health data values for a specific WHO Global Health Observatory indicator by its code....
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def WHOGHO_get_indicator_data(
    indicator_code: str,
    filter: Optional[str] = None,
    top: Optional[int] = 100,
    orderby: Optional[str] = None,
    skip: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get actual health data values for a specific WHO Global Health Observatory indicator by its code....

    Parameters
    ----------
    indicator_code : str
        WHO GHO indicator code. Examples: 'WHOSIS_000001' (life expectancy), 'MALARIA...
    filter : str
        OData filter for data rows. Examples: "SpatialDim eq 'USA'", "TimeDim eq 2022...
    top : int
        Maximum number of data rows to return per page (default 100, max 1000). One r...
    orderby : str
        OData $orderby clause controlling row order, which also determines which rows...
    skip : int
        Zero-based OData offset. Continue with metadata.next_skip.
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
            "indicator_code": indicator_code,
            "filter": filter,
            "top": top,
            "orderby": orderby,
            "skip": skip,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "WHOGHO_get_indicator_data",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["WHOGHO_get_indicator_data"]
