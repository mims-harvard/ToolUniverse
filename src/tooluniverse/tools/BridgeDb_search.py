"""
BridgeDb_search

Search for biological identifiers by name using BridgeDb. Enter a gene name, metabolite name, or ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BridgeDb_search(
    operation: str,
    query: str,
    organism: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search for biological identifiers by name using BridgeDb. Enter a gene name, metabolite name, or ...

    Parameters
    ----------
    operation : str
        Operation type (fixed: search)
    query : str
        Name to search for (e.g., 'glucose', 'TP53', 'ATP')
    organism : str
        Organism name (default: Human). Options: Human, Mouse, Rat, Yeast, Worm, Frui...
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
        {
            "name": "BridgeDb_search",
            "arguments": {"operation": operation, "query": query, "organism": organism},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BridgeDb_search"]
