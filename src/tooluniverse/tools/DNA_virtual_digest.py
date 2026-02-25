"""
DNA_virtual_digest

Perform a virtual restriction enzyme digest on a DNA sequence using the NEB enzyme library (24 en...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DNA_virtual_digest(
    operation: str,
    sequence: str,
    enzymes: Optional[list[str] | Any] = None,
    circular: Optional[bool | Any] = False,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Perform a virtual restriction enzyme digest on a DNA sequence using the NEB enzyme library (24 en...

    Parameters
    ----------
    operation : str
        Operation type
    sequence : str
        DNA sequence (A, T, G, C, N only). Case insensitive.
    enzymes : list[str] | Any
        List of enzyme names to use for digestion (e.g., ['EcoRI', 'BamHI']). If null...
    circular : bool | Any
        Treat sequence as circular DNA (e.g., plasmid). Default: false (linear).
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
            "name": "DNA_virtual_digest",
            "arguments": {
                "operation": operation,
                "sequence": sequence,
                "enzymes": enzymes,
                "circular": circular,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DNA_virtual_digest"]
