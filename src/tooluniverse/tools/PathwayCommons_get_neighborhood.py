"""
PathwayCommons_get_neighborhood

Get the interaction neighborhood for a gene from Pathway Commons. Returns all known interactions ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PathwayCommons_get_neighborhood(
    gene: str,
    limit: Optional[int | Any] = 1,
    datasource: Optional[str | Any] = None,
    max_results: Optional[int | Any] = 100,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get the interaction neighborhood for a gene from Pathway Commons. Returns all known interactions ...

    Parameters
    ----------
    gene : str
        Gene symbol (e.g., BRCA1, TP53, EGFR)
    limit : int | Any
        Graph search depth (1 = direct neighbors, 2 = neighbors of neighbors). Defaul...
    datasource : str | Any
        Filter by data source: reactome, kegg, biogrid, intact, hprd, pid, corum, ctd...
    max_results : int | Any
        Maximum number of interactions to return (default: 100)
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
            "gene": gene,
            "limit": limit,
            "datasource": datasource,
            "max_results": max_results,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PathwayCommons_get_neighborhood",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PathwayCommons_get_neighborhood"]
