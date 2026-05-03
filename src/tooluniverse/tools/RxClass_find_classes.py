"""
RxClass_find_classes

Search NLM RxClass drug classification database by keyword. Returns matching class IDs, names, an...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def RxClass_find_classes(
    query: str,
    class_type: Optional[str | Any] = None,
    limit: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search NLM RxClass drug classification database by keyword. Returns matching class IDs, names, an...

    Parameters
    ----------
    query : str
        Keyword to search in class names. Examples: 'analgesic', 'beta blocker', 'ant...
    class_type : str | Any
        Filter by class type. Options: 'ATC1-4' (ATC codes), 'EPC' (Established Pharm...
    limit : int | Any
        Maximum results to return (default 20).
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
        for k, v in {"query": query, "class_type": class_type, "limit": limit}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "RxClass_find_classes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["RxClass_find_classes"]
