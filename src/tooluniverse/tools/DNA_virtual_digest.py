"""
DNA_virtual_digest

Perform a virtual restriction enzyme digest on a DNA sequence using the NEB enzyme library (25 cu...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DNA_virtual_digest(
    sequence: str,
    operation: Optional[str] = "virtual_digest",
    enzymes: Optional[list[str]] = None,
    circular: Optional[bool] = False,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Perform a virtual restriction enzyme digest on a DNA sequence using the NEB enzyme library (25 cu...

    Parameters
    ----------
    operation : str
        Operation (optional; defaults to 'virtual_digest' for this tool).
    sequence : str
        DNA sequence (A, T, G, C, N only). Case insensitive.
    enzymes : list[str]
        List of enzyme names to use for digestion (e.g., ['EcoRI', 'BamHI']). If null...
    circular : bool
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

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "operation": operation,
            "sequence": sequence,
            "enzymes": enzymes,
            "circular": circular,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "DNA_virtual_digest",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DNA_virtual_digest"]
