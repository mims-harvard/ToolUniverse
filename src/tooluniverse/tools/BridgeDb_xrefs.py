"""
BridgeDb_xrefs

Map a biological identifier across databases using BridgeDb. Given an identifier from one databas...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BridgeDb_xrefs(
    operation: str,
    identifier: str,
    source: str,
    organism: Optional[str] = None,
    target_source: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Map a biological identifier across databases using BridgeDb. Given an identifier from one databas...

    Parameters
    ----------
    operation : str
        Operation type (fixed: xrefs)
    identifier : str
        The identifier to look up (e.g., 'HMDB0000122' for glucose, 'ENSG00000141510'...
    source : str
        Source database name or system code. Common codes: Ch=HMDB, Ce=ChEBI, Ck=KEGG...
    organism : str
        Organism name (default: Human). Options include: Human, Mouse, Rat, Yeast, Wo...
    target_source : str
        Optional: filter results to a specific target database. Use database name or ...
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
            "name": "BridgeDb_xrefs",
            "arguments": {
                "operation": operation,
                "identifier": identifier,
                "source": source,
                "organism": organism,
                "target_source": target_source,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BridgeDb_xrefs"]
