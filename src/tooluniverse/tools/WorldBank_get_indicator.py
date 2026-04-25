"""
WorldBank_get_indicator

Get World Bank development indicator data for one or more countries over time. Returns economic, ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def WorldBank_get_indicator(
    country: str,
    indicator: str,
    mrv: Optional[int | Any] = None,
    date: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get World Bank development indicator data for one or more countries over time. Returns economic, ...

    Parameters
    ----------
    country : str
        ISO 3166-1 alpha-3 country code (e.g., 'USA', 'GBR', 'DEU', 'CHN', 'IND', 'BR...
    indicator : str
        World Bank indicator code (e.g., 'NY.GDP.MKTP.CD' for GDP, 'SP.POP.TOTL' for ...
    mrv : int | Any
        Most recent values - number of most recent years to return (e.g., 5 for last ...
    date : str | Any
        Year or year range to filter data (e.g., '2020', '2015:2023' for a range)
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
    _args = {k: v for k, v in {
        "country": country,
                "indicator": indicator,
                "mrv": mrv,
                "date": date
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "WorldBank_get_indicator",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["WorldBank_get_indicator"]
