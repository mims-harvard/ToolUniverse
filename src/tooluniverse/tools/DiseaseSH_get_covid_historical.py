"""
DiseaseSH_get_covid_historical

Get historical COVID-19 timeline data (cases, deaths, recoveries) for a country or globally using...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DiseaseSH_get_covid_historical(
    country: Optional[str | Any] = None,
    lastdays: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get historical COVID-19 timeline data (cases, deaths, recoveries) for a country or globally using...

    Parameters
    ----------
    country : str | Any
        Country name or ISO code. Use 'all' for global data. Examples: 'usa', 'china'...
    lastdays : int | Any
        Number of past days to include. Use 'all' for full history. Default: 30. Exam...
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
        for k, v in {"country": country, "lastdays": lastdays}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "DiseaseSH_get_covid_historical",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DiseaseSH_get_covid_historical"]
