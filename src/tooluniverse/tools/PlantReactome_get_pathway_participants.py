"""
PlantReactome_get_pathway_participants

List the gene/protein/molecule participants of a Plant Reactome pathway or reaction (the macromol...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PlantReactome_get_pathway_participants(
    pathway_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List the gene/protein/molecule participants of a Plant Reactome pathway or reaction (the macromol...

    Parameters
    ----------
    pathway_id : str
        Plant Reactome stable identifier of a pathway or reaction. Format: R-{species...
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
            "name": "PlantReactome_get_pathway_participants",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PlantReactome_get_pathway_participants"]
