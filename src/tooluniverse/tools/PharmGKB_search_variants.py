"""
PharmGKB_search_variants

Search for genetic variants in PharmGKB by rsID or name. Returns variant IDs and associated gene ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PharmGKB_search_variants(
    query: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search for genetic variants in PharmGKB by rsID or name. Returns variant IDs and associated gene ...

    Parameters
    ----------
    query : str
        Variant name or rsID (e.g., 'rs1799853').
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
    _args = {k: v for k, v in {"query": query}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "PharmGKB_search_variants",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PharmGKB_search_variants"]
