"""
Bioregistry_search_registries

Search the Bioregistry for databases, ontologies, and resources by keyword. Use to find the corre...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Bioregistry_search_registries(
    query: str,
    operation: Optional[str] = None,
    limit: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search the Bioregistry for databases, ontologies, and resources by keyword. Use to find the corre...

    Parameters
    ----------
    operation : str
        Operation type (fixed: search_registries)
    query : str
        Search term (e.g., 'protein', 'gene expression', 'metabolite')
    limit : int
        Maximum results to return (default: 10)
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
        for k, v in {"operation": operation, "query": query, "limit": limit}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Bioregistry_search_registries",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Bioregistry_search_registries"]
