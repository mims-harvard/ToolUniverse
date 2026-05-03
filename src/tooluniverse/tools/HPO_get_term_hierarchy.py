"""
HPO_get_term_hierarchy

Get the parent or child terms of an HPO phenotype term in the ontology hierarchy. HPO is organize...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def HPO_get_term_hierarchy(
    term_id: str,
    direction: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the parent or child terms of an HPO phenotype term in the ontology hierarchy. HPO is organize...

    Parameters
    ----------
    term_id : str
        HPO term identifier (e.g., 'HP:0001250'). Must start with 'HP:' followed by 7...
    direction : str | Any
        Direction to traverse: 'children' (more specific terms, default) or 'parents'...
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
        for k, v in {"term_id": term_id, "direction": direction}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "HPO_get_term_hierarchy",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["HPO_get_term_hierarchy"]
