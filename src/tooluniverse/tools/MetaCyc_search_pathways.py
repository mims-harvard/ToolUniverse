"""
MetaCyc_search_pathways

Search MetaCyc for metabolic pathways by name or keyword. Returns pathway IDs and basic informati...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MetaCyc_search_pathways(
    query: str,
    operation: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search MetaCyc for metabolic pathways by name or keyword. Returns pathway IDs and basic informati...

    Parameters
    ----------
    operation : str

    query : str
        Search query - pathway name or keyword (e.g., 'glycolysis', 'TCA cycle')
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
        for k, v in {"operation": operation, "query": query}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MetaCyc_search_pathways",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MetaCyc_search_pathways"]
