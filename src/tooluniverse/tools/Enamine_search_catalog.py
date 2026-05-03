"""
Enamine_search_catalog

Search Enamine compound catalog by keyword or name. Enamine is a leading supplier with 37B+ make-...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Enamine_search_catalog(
    query: str,
    operation: Optional[str] = None,
    catalog: Optional[str] = "all",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search Enamine compound catalog by keyword or name. Enamine is a leading supplier with 37B+ make-...

    Parameters
    ----------
    operation : str

    query : str
        Search query - compound name or keyword
    catalog : str
        Catalog: REAL (make-on-demand), BB (building blocks), SCR (screening), all (d...
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
        for k, v in {"operation": operation, "query": query, "catalog": catalog}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Enamine_search_catalog",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Enamine_search_catalog"]
