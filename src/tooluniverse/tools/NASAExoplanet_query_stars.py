"""
NASAExoplanet_query_stars

Query the NASA Exoplanet Archive for stellar host properties using ADQL SQL. Use table 'stellarho...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NASAExoplanet_query_stars(
    query: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Query the NASA Exoplanet Archive for stellar host properties using ADQL SQL. Use table 'stellarho...

    Parameters
    ----------
    query : str
        ADQL/SQL query against NASA Exoplanet Archive. Use 'stellarhosts' table for s...
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
        "query": query
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "NASAExoplanet_query_stars",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["NASAExoplanet_query_stars"]
