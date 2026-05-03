"""
WHOGHO_search_indicators

Search WHO Global Health Observatory (GHO) health indicators by name using the ODATA API. Returns...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def WHOGHO_search_indicators(
    filter: Optional[str | Any] = None,
    top: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search WHO Global Health Observatory (GHO) health indicators by name using the ODATA API. Returns...

    Parameters
    ----------
    filter : str | Any
        OData filter string for indicator names. Examples: "contains(IndicatorName,'m...
    top : int | Any
        Maximum number of results to return. Default: 10, max: 100
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
    _args = {k: v for k, v in {"filter": filter, "top": top}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "WHOGHO_search_indicators",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["WHOGHO_search_indicators"]
