"""
MonarchV3_get_associations

Query cross-species associations between biomedical entities in the Monarch Initiative knowledge ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MonarchV3_get_associations(
    category: str,
    subject: Optional[str] = None,
    object: Optional[str] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Query cross-species associations between biomedical entities in the Monarch Initiative knowledge ...

    Parameters
    ----------
    subject : str
        Subject-side entity CURIE, i.e. the entity on the LEFT of the association (th...
    object : str
        Object-side entity CURIE, i.e. the entity on the RIGHT of the association (th...
    category : str
        Biolink association category, written as subject->object. Options: 'biolink:G...
    limit : int
        Maximum number of associations to return (default: 20, max: 200).
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
        for k, v in {
            "subject": subject,
            "object": object,
            "category": category,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MonarchV3_get_associations",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MonarchV3_get_associations"]
