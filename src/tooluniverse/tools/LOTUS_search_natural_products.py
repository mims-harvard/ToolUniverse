"""
LOTUS_search_natural_products

Search the LOTUS (naturaL prOducTs occUrrenceS) database for natural products by name, SMILES, or...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def LOTUS_search_natural_products(
    query: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the LOTUS (naturaL prOducTs occUrrenceS) database for natural products by name, SMILES, or...

    Parameters
    ----------
    query : str
        Search query: compound name (e.g., 'caffeine', 'quercetin'), SMILES string, o...
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

    return get_shared_client().run_one_function(
        {"name": "LOTUS_search_natural_products", "arguments": {"query": query}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["LOTUS_search_natural_products"]
