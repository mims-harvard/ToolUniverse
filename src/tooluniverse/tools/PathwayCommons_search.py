"""
PathwayCommons_search

Search Pathway Commons for pathways, interactions, and molecular entities across 22 integrated da...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PathwayCommons_search(
    query: str,
    type_: Optional[str | Any] = None,
    datasource: Optional[str | Any] = None,
    organism: Optional[str | Any] = None,
    page: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search Pathway Commons for pathways, interactions, and molecular entities across 22 integrated da...

    Parameters
    ----------
    query : str
        Search query: gene symbol (BRCA1, TP53), protein name, pathway name, or keyword
    type_ : str | Any
        BioPAX entity type filter (default: all types)
    datasource : str | Any
        Data source filter: reactome, kegg, wikipathways, pid, biogrid, intact, hprd,...
    organism : str | Any
        Organism filter: taxonomy ID (9606 for human, 10090 for mouse) or organism name
    page : int | Any
        Page number for pagination (0-based, 100 results per page)
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
        for k, v in {
            "query": query,
            "type": type_,
            "datasource": datasource,
            "organism": organism,
            "page": page,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PathwayCommons_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PathwayCommons_search"]
