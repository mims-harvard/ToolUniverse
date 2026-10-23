"""
CoL_get_children

Get immediate child taxa of a Catalogue of Life taxon through the official tree/{id}/children end...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CoL_get_children(
    parentId: str,
    limit: Optional[int] = 10,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get immediate child taxa of a Catalogue of Life taxon through the official tree/{id}/children end...

    Parameters
    ----------
    parentId : str
        CoL ID of the parent taxon whose children to retrieve (e.g., '636X2' for genu...
    limit : int
        Maximum number of children to return (default 10, max 1000)
    offset : int
        Offset for pagination
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
        for k, v in {"parentId": parentId, "limit": limit, "offset": offset}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "CoL_get_children",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CoL_get_children"]
