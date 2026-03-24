"""
HMDB_search

Alias for Metabolite_search. Search for metabolites by compound name or molecular formula via Pub...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def HMDB_search(
    query: str,
    operation: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Alias for Metabolite_search. Search for metabolites by compound name or molecular formula via Pub...

    Parameters
    ----------
    operation : str

    query : str
        Compound name or molecular formula to search
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
        for k, v in {"operation": operation, "query": query}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "HMDB_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["HMDB_search"]
