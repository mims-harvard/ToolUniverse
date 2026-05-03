"""
PlantReactome_get_pathway

Get detailed information about a specific Plant Reactome pathway by stable ID. Returns pathway na...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PlantReactome_get_pathway(
    pathway_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed information about a specific Plant Reactome pathway by stable ID. Returns pathway na...

    Parameters
    ----------
    pathway_id : str
        Plant Reactome stable identifier. Format: R-{species_code}-{number}. Examples...
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
    _args = {k: v for k, v in {"pathway_id": pathway_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "PlantReactome_get_pathway",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PlantReactome_get_pathway"]
