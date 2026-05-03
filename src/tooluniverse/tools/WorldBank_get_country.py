"""
WorldBank_get_country

Get metadata about a country from the World Bank database. Returns country name, ISO codes, world...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def WorldBank_get_country(
    country: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get metadata about a country from the World Bank database. Returns country name, ISO codes, world...

    Parameters
    ----------
    country : str
        ISO 3166-1 alpha-2 or alpha-3 country code (e.g., 'US' or 'USA' for United St...
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
    _args = {k: v for k, v in {"country": country}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "WorldBank_get_country",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["WorldBank_get_country"]
