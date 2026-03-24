"""
RxClass_find_classes

Search NLM RxClass drug classification database by keyword.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def RxClass_find_classes(
    query: str,
    class_type: Optional[str] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search NLM RxClass drug classification database by keyword.

    Parameters
    ----------
    query : str
        Keyword to search in class names (e.g., 'analgesic', 'beta blocker', 'statin').
    class_type : str, optional
        Filter by class type: 'ATC1-4', 'EPC', 'MOA', 'PE', 'DISEASE', 'VA', 'SCHEDULE'.
    limit : int, optional
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
    _args = {
        k: v
        for k, v in {
            "query": query,
            "class_type": class_type,
            "limit": limit,
        }.items()
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
