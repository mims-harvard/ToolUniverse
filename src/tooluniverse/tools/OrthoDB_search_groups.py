"""
OrthoDB_search_groups

Search for orthologous groups by gene/protein name in OrthoDB v12. OrthoDB catalogs orthologous g...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OrthoDB_search_groups(
    query: str,
    species: Optional[int | Any] = None,
    level: Optional[int | Any] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search for orthologous groups by gene/protein name in OrthoDB v12. OrthoDB catalogs orthologous g...

    Parameters
    ----------
    query : str
        Gene or protein name to search. Examples: 'BRCA1', 'TP53', 'insulin', 'EGFR'.
    species : int | Any
        NCBI taxonomy ID to filter by species. Examples: 9606 (human), 10090 (mouse),...
    level : int | Any
        Taxonomic level for group definition. Examples: 7742 (Vertebrata), 33208 (Met...
    limit : int
        Maximum number of groups to return (1-50). Default: 10.
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
            "name": "OrthoDB_search_groups",
            "arguments": {
                "query": query,
                "species": species,
                "level": level,
                "limit": limit,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OrthoDB_search_groups"]
