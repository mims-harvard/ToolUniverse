"""
WorldBank_search_indicators

Search World Bank for development indicators by keyword. Returns indicator codes, names, descript...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def WorldBank_search_indicators(
    query: str,
    per_page: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search World Bank for development indicators by keyword. Returns indicator codes, names, descript...

    Parameters
    ----------
    query : str
        Search keyword for indicators (e.g., 'GDP', 'mortality', 'literacy', 'CO2', '...
    per_page : int | Any
        Number of results to return (default 10, max 1000)
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
        k: v for k, v in {"query": query, "per_page": per_page}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "WorldBank_search_indicators",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["WorldBank_search_indicators"]
