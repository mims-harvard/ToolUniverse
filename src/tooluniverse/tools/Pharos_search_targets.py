"""
Pharos_search_targets

Search drug targets in Pharos database by keyword. Supports filtering by Target Development Level...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Pharos_search_targets(
    query: str,
    tdl: Optional[str] = None,
    top: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search drug targets in Pharos database by keyword. Supports filtering by Target Development Level...

    Parameters
    ----------
    query : str
        Search query (gene name, protein name, or keyword)
    tdl : str
        Filter by Target Development Level. Tdark=understudied, Tbio=biological annot...
    top : int
        Maximum number of results (1-100)
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
    _args = {
        k: v
        for k, v in {"query": query, "tdl": tdl, "top": top}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Pharos_search_targets",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Pharos_search_targets"]
