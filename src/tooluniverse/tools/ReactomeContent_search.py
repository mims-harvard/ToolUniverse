"""
ReactomeContent_search

Search Reactome for pathways, reactions, and biological entities by keyword. Performs free-text s...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ReactomeContent_search(
    query: str,
    species: Optional[str] = "Homo sapiens",
    types: Optional[str] = "Pathway",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search Reactome for pathways, reactions, and biological entities by keyword. Performs free-text s...

    Parameters
    ----------
    query : str
        Search query. Examples: 'apoptosis', 'TP53', 'cell cycle', 'DNA repair', 'ins...
    species : str
        Species name for filtering results. Default: 'Homo sapiens'. Other options: '...
    types : str
        Entity type to search. Options: 'Pathway', 'Reaction', 'Complex', 'Protein', ...
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
            "name": "ReactomeContent_search",
            "arguments": {"query": query, "species": species, "types": types},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ReactomeContent_search"]
