"""
DBpedia_SPARQL_query

Execute SELECT or ASK queries against the public DBpedia SPARQL endpoint. SELECT results are reco...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DBpedia_SPARQL_query(
    sparql: str,
    max_results: Optional[int] = None,
    offset: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Execute SELECT or ASK queries against the public DBpedia SPARQL endpoint. SELECT results are reco...

    Parameters
    ----------
    sparql : str
        SPARQL query string to execute against DBpedia. Use SPARQL syntax to query en...
    max_results : int
        Optional SELECT page size override (1-1000). If omitted, use the terminal que...
    offset : int
        Optional zero-based SELECT result offset. Continue with data.next_offset whil...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "sparql": sparql,
            "max_results": max_results,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "DBpedia_SPARQL_query",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DBpedia_SPARQL_query"]
