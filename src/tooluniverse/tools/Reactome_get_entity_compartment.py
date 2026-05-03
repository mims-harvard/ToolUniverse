"""
Reactome_get_entity_compartment

Get compartment information for an entity. Returns TSV-formatted compartment data parsed into str...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Reactome_get_entity_compartment(
    stId: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get compartment information for an entity. Returns TSV-formatted compartment data parsed into str...

    Parameters
    ----------
    stId : str
        Entity Stable ID (e.g., 'R-HSA-73817'). To find pathway IDs, use Reactome_lis...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {"stId": stId}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "Reactome_get_entity_compartment",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Reactome_get_entity_compartment"]
