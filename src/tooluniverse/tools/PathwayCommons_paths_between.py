"""
PathwayCommons_paths_between

Find mechanistic interaction paths connecting a set of genes/proteins in Pathway Commons (PC2 kin...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PathwayCommons_paths_between(
    genes: list[str],
    limit: Optional[int] = 1,
    datasource: Optional[str] = None,
    max_results: Optional[int] = 200,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Find mechanistic interaction paths connecting a set of genes/proteins in Pathway Commons (PC2 kin...

    Parameters
    ----------
    genes : list[str]
        Two or more gene symbols / identifiers to connect, e.g. ["BRCA1", "BRCA2", "T...
    limit : int
        Path length limit (graph search distance). Default 1 (direct mechanistic link...
    datasource : str
        Filter by data source: reactome, kegg, biogrid, intact, hprd, pid, corum, ctd...
    max_results : int
        Maximum number of edges to return (default: 200)
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
        for k, v in {
            "genes": genes,
            "limit": limit,
            "datasource": datasource,
            "max_results": max_results,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PathwayCommons_paths_between",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PathwayCommons_paths_between"]
