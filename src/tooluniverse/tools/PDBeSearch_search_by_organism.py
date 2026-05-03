"""
PDBeSearch_search_by_organism

Search PDB structures filtered by organism through PDBe's Solr search. Combines keyword search wi...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PDBeSearch_search_by_organism(
    organism: str,
    query: Optional[str | Any] = None,
    limit: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search PDB structures filtered by organism through PDBe's Solr search. Combines keyword search wi...

    Parameters
    ----------
    organism : str
        Scientific name of organism. Examples: 'Homo sapiens', 'Escherichia coli', 'M...
    query : str | Any
        Optional keyword query to combine with organism filter. Examples: 'kinase', '...
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
    _args = {
        k: v
        for k, v in {"organism": organism, "query": query, "limit": limit}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PDBeSearch_search_by_organism",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PDBeSearch_search_by_organism"]
