"""
DiseaseSH_get_vaccine_coverage

Get COVID-19 vaccine coverage data for a country or globally using the Disease.sh API. Returns ti...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DiseaseSH_get_vaccine_coverage(
    country: Optional[str | Any] = None,
    lastdays: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get COVID-19 vaccine coverage data for a country or globally using the Disease.sh API. Returns ti...

    Parameters
    ----------
    country : str | Any
        Country name or 'all' for global. Examples: 'usa', 'uk', 'germany', 'india', ...
    lastdays : int | Any
        Number of past days to include. Default: 30. Examples: 7, 30, 90
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
                "lastdays": lastdays
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "DiseaseSH_get_vaccine_coverage",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["DiseaseSH_get_vaccine_coverage"]
