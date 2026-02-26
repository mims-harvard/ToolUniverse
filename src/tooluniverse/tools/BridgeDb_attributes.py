"""
BridgeDb_attributes

Get properties and attributes for a biological identifier from BridgeDb. Returns metadata such as...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BridgeDb_attributes(
    operation: str,
    identifier: str,
    source: str,
    organism: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get properties and attributes for a biological identifier from BridgeDb. Returns metadata such as...

    Parameters
    ----------
    operation : str
        Operation type (fixed: attributes)
    identifier : str
        The identifier to look up (e.g., 'HMDB0000122' for glucose, '17234' for ChEBI...
    source : str
        Source database name or system code. Common: Ch=HMDB, Ce=ChEBI, Ck=KEGG Compo...
    organism : str
        Organism name (default: Human). Options: Human, Mouse, Rat, Yeast, etc.
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
            "name": "BridgeDb_attributes",
            "arguments": {
                "operation": operation,
                "identifier": identifier,
                "source": source,
                "organism": organism,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BridgeDb_attributes"]
