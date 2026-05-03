"""
Wikidata_SPARQL_query

Execute SPARQL queries against Wikidata to retrieve structured data. This tool powers Scholia-sty...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Wikidata_SPARQL_query(
    sparql: str,
    max_results: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Execute SPARQL queries against Wikidata to retrieve structured data. This tool powers Scholia-sty...

    Parameters
    ----------
    sparql : str
        SPARQL query string to execute against Wikidata. Use SPARQL syntax to query a...
    max_results : int
        Optional result limit override. If not specified, uses the LIMIT clause in th...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {"sparql": sparql, "max_results": max_results}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Wikidata_SPARQL_query",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Wikidata_SPARQL_query"]
