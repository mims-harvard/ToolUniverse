"""
PlantReactome_get_species_pathway_tree

Retrieve the full hierarchical pathway/event tree for a plant species (top-level pathways down to...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PlantReactome_get_species_pathway_tree(
    tax_id: str | int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve the full hierarchical pathway/event tree for a plant species (top-level pathways down to...

    Parameters
    ----------
    tax_id : str | int
        NCBI taxonomy id of the plant species. Examples: 4530 (Oryza sativa / rice), ...
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
    _args = {k: v for k, v in {"tax_id": tax_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "PlantReactome_get_species_pathway_tree",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PlantReactome_get_species_pathway_tree"]
