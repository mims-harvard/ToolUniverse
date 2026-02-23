"""
USCensus_get_population

Get population and demographic data from the US Census Bureau API. Access decennial census and Am...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def USCensus_get_population(
    get: str,
    for_: str,
    dataset: Optional[str | Any] = None,
    in_: Optional[str | Any] = None,
    limit: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get population and demographic data from the US Census Bureau API. Access decennial census and Am...

    Parameters
    ----------
    get : str
        Comma-separated variable codes to retrieve plus NAME. For 2020 decennial: 'P1...
    for_ : str
        Geographic unit. Examples: 'state:*' (all states), 'county:*' (all counties),...
    dataset : str | Any
        Dataset to query. Values: '2020/dec/pl' (2020 decennial), '2022/acs/acs5' (AC...
    in_ : str | Any
        Geographic filter for sub-national queries. Examples: 'state:06' (within Cali...
    limit : int | Any
        Maximum number of results to return
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

    return get_shared_client().run_one_function(
        {
            "name": "USCensus_get_population",
            "arguments": {
                "get": get,
                "for": for_,
                "dataset": dataset,
                "in": in_,
                "limit": limit,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["USCensus_get_population"]
