"""
NASAExoplanet_query_planets

Query the NASA Exoplanet Archive for confirmed exoplanets using SQL-like ADQL queries. Returns or...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NASAExoplanet_query_planets(
    query: str,
    format: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Query the NASA Exoplanet Archive for confirmed exoplanets using SQL-like ADQL queries. Returns or...

    Parameters
    ----------
    query : str
        ADQL/SQL query against the NASA Exoplanet Archive table 'ps'. Note: LIMIT is ...
    format : str | Any
        Output format: 'json' (default), 'csv', 'tsv', 'votable'
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
            "name": "NASAExoplanet_query_planets",
            "arguments": {"query": query, "format": format},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NASAExoplanet_query_planets"]
