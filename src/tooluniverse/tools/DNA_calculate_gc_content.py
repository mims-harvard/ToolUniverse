"""
DNA_calculate_gc_content

Calculate GC content percentage and full nucleotide composition of a DNA sequence. Returns GC%, A...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DNA_calculate_gc_content(
    operation: str,
    sequence: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Calculate GC content percentage and full nucleotide composition of a DNA sequence. Returns GC%, A...

    Parameters
    ----------
    operation : str
        Operation type
    sequence : str
        DNA sequence (A, T, G, C, N only). Case insensitive.
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

    return get_shared_client().run_one_function(
        {
            "name": "DNA_calculate_gc_content",
            "arguments": {"operation": operation, "sequence": sequence},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DNA_calculate_gc_content"]
