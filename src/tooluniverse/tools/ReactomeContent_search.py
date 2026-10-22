"""
ReactomeContent_search

Search and page through Reactome pathways, reactions, and biological entities by keyword. Uses Re...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ReactomeContent_search(
    query: str,
    species: Optional[str] = "Homo sapiens",
    types: Optional[str] = "Pathway",
    limit: Optional[int] = 30,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search and page through Reactome pathways, reactions, and biological entities by keyword. Uses Re...

    Parameters
    ----------
    query : str
        Search query. Examples: 'apoptosis', 'TP53', 'cell cycle', 'DNA repair', 'ins...
    species : str
        Species name for filtering results. Default: 'Homo sapiens'. Other options: '...
    types : str
        Entity type to search. Options: 'Pathway', 'Reaction', 'Complex', 'Protein', ...
    limit : int
        Number of Reactome search rows to request.
    offset : int
        Zero-based Reactome search start row.
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
            "query": query,
            "species": species,
            "types": types,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ReactomeContent_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ReactomeContent_search"]
