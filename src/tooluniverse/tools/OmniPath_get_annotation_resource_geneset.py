"""
OmniPath_get_annotation_resource_geneset

Retrieve the ENTIRE annotated gene/protein set (resource-wide membership) for an OmniPath annotat...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OmniPath_get_annotation_resource_geneset(
    resource: str,
    entity_types: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve the ENTIRE annotated gene/protein set (resource-wide membership) for an OmniPath annotat...

    Parameters
    ----------
    resource : str
        Name of the OmniPath annotation resource whose full gene/protein set to retri...
    entity_types : str
        Optional filter on entity type, comma-separated. Options: 'protein', 'complex...
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
        for k, v in {"resource": resource, "entity_types": entity_types}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OmniPath_get_annotation_resource_geneset",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OmniPath_get_annotation_resource_geneset"]
