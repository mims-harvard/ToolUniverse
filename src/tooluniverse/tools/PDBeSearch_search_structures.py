"""
PDBeSearch_search_structures

Search PDB structures through PDBe's Solr search interface by keyword, protein name, or gene name...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PDBeSearch_search_structures(
    query: str,
    limit: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search PDB structures through PDBe's Solr search interface by keyword, protein name, or gene name...

    Parameters
    ----------
    query : str
        Search query - protein name, gene name, or keyword. Supports Solr syntax. Exa...
    limit : int | Any
        Maximum results to return (1-50, default 10).
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
            "name": "PDBeSearch_search_structures",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PDBeSearch_search_structures"]
