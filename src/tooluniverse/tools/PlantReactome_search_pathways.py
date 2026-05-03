"""
PlantReactome_search_pathways

Search for plant biological pathways in Plant Reactome (Gramene). Plant Reactome is a curated res...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PlantReactome_search_pathways(
    query: str,
    species: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search for plant biological pathways in Plant Reactome (Gramene). Plant Reactome is a curated res...

    Parameters
    ----------
    query : str
        Search query for plant pathways. Examples: 'photosynthesis', 'Calvin cycle', ...
    species : str | Any
        Species name to filter results. Examples: 'Oryza sativa', 'Arabidopsis thalia...
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
        k: v for k, v in {"query": query, "species": species}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PlantReactome_search_pathways",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PlantReactome_search_pathways"]
