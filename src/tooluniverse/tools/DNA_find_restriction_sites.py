"""
DNA_find_restriction_sites

Find restriction enzyme recognition sites in a DNA sequence using the NEB enzyme library (24 comm...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DNA_find_restriction_sites(
    operation: str,
    sequence: str,
    enzymes: Optional[list[str] | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Find restriction enzyme recognition sites in a DNA sequence using the NEB enzyme library (24 comm...

    Parameters
    ----------
    operation : str
        Operation type
    sequence : str
        DNA sequence (A, T, G, C, N only). Case insensitive. Spaces and newlines are ...
    enzymes : list[str] | Any
        Optional list of specific enzyme names to check (e.g., ['EcoRI', 'BamHI']). I...
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
    _args = {k: v for k, v in {
        "operation": operation,
                "sequence": sequence,
                "enzymes": enzymes
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "DNA_find_restriction_sites",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["DNA_find_restriction_sites"]
