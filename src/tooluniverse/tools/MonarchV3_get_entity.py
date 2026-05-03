"""
MonarchV3_get_entity

Look up detailed information about any biomedical entity in the Monarch Initiative knowledge grap...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MonarchV3_get_entity(
    entity_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Look up detailed information about any biomedical entity in the Monarch Initiative knowledge grap...

    Parameters
    ----------
    entity_id : str
        Entity CURIE identifier. Examples: 'HGNC:11998' (TP53), 'HGNC:1100' (BRCA1), ...
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
    _args = {k: v for k, v in {"entity_id": entity_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "MonarchV3_get_entity",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MonarchV3_get_entity"]
