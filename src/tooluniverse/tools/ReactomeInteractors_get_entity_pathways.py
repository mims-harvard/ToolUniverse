"""
ReactomeInteractors_get_entity_pathways

Find Reactome biological pathways that contain a specific molecular entity. Returns pathway stabl...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ReactomeInteractors_get_entity_pathways(
    entity_id: str,
    species: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Find Reactome biological pathways that contain a specific molecular entity. Returns pathway stabl...

    Parameters
    ----------
    entity_id : str
        Reactome stable identifier for the entity. Use ReactomeInteractors_search_ent...
    species : int | Any
        NCBI taxonomy ID for species filter (default: 9606 for human). Examples: 9606...
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
            "name": "ReactomeInteractors_get_entity_pathways",
            "arguments": {"entity_id": entity_id, "species": species},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ReactomeInteractors_get_entity_pathways"]
