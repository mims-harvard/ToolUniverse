"""
MDDB_search_projects

Search MDDB, an index of over 15,000 molecular dynamics simulation trajectories (MoDEL, BioExcel,...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MDDB_search_projects(
    query: str,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search MDDB, an index of over 15,000 molecular dynamics simulation trajectories (MoDEL, BioExcel,...

    Parameters
    ----------
    query : str
        Protein name or PDB id, e.g. 'kinase', '6M71'.
    limit : int
        Max projects to return, 1-100. Default 25.
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
    _args = {k: v for k, v in {"query": query, "limit": limit}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "MDDB_search_projects",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MDDB_search_projects"]
