"""
PharmGKB_search_genes

Search for genes in PharmGKB by name, symbol, or ID. Returns PharmGKB Gene ID and basic gene meta...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PharmGKB_search_genes(
    query: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search for genes in PharmGKB by name, symbol, or ID. Returns PharmGKB Gene ID and basic gene meta...

    Parameters
    ----------
    query : str
        Gene name, symbol, or PharmGKB Accession ID (e.g., 'CYP2D6', 'PA128').
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
            "name": "PharmGKB_search_genes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PharmGKB_search_genes"]
