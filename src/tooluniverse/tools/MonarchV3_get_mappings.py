"""
MonarchV3_get_mappings

Get cross-ontology mappings for a biomedical entity from the Monarch Initiative. Returns equivale...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MonarchV3_get_mappings(
    entity_id: str,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get cross-ontology mappings for a biomedical entity from the Monarch Initiative. Returns equivale...

    Parameters
    ----------
    entity_id : str
        Entity CURIE identifier to find mappings for. Examples: 'MONDO:0005148' (type...
    limit : int
        Maximum number of mappings to return (default: 20, max: 100).
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {"entity_id": entity_id, "limit": limit}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MonarchV3_get_mappings",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MonarchV3_get_mappings"]
