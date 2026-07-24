"""
ReactomeAnalysis_species_comparison_v2

True cross-species pathway comparison (analysis type=SPECIES_COMPARISON). Compares one species' p...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ReactomeAnalysis_species_comparison_v2(
    species: int,
    source_species: Optional[str] = None,
    page_size: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    True cross-species pathway comparison (analysis type=SPECIES_COMPARISON). Compares one species' p...

    Parameters
    ----------
    species : int
        Reactome species dbId of the species to compare against the source. NOTE: thi...
    source_species : str
        Source species name in Reactome lowerCamelCase form (default 'homoSapiens'). ...
    page_size : int
        Number of pathways to return (default 20, max 50).
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
            "species": species,
            "source_species": source_species,
            "page_size": page_size,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ReactomeAnalysis_species_comparison_v2",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ReactomeAnalysis_species_comparison_v2"]
