"""
ReactomeInteractors_search_entity

Search Reactome for biological entities (proteins, complexes, reactions, pathways) by name or ide...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ReactomeInteractors_search_entity(
    query: str,
    species: Optional[str | Any] = None,
    types: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search Reactome for biological entities (proteins, complexes, reactions, pathways) by name or ide...

    Parameters
    ----------
    query : str
        Search query - gene name, protein name, pathway name, or Reactome ID. Example...
    species : str | Any
        Species name filter (default: 'Homo sapiens'). Examples: 'Homo sapiens', 'Mus...
    types : str | Any
        Entity type filter. Options: 'Protein', 'Complex', 'Reaction', 'Pathway', 'Sm...
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
        for k, v in {"query": query, "species": species, "types": types}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ReactomeInteractors_search_entity",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ReactomeInteractors_search_entity"]
