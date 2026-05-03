"""
CMA_Guidelines_Search

Search Canadian Medical Association (CMA) Infobase guidelines. Contains over 1200 evidence-based ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CMA_Guidelines_Search(
    query: str,
    limit: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search Canadian Medical Association (CMA) Infobase guidelines. Contains over 1200 evidence-based ...

    Parameters
    ----------
    query : str
        Medical condition, treatment, or clinical topic to search for in CMA guidelin...
    limit : int
        Maximum number of guidelines to return (default: 10)
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
    _args = {k: v for k, v in {"query": query, "limit": limit}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "CMA_Guidelines_Search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CMA_Guidelines_Search"]
