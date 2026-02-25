"""
DNA_reverse_complement

Generate the reverse complement of a DNA sequence. Complements each base (A↔T, G↔C) then reverses...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DNA_reverse_complement(
    operation: str,
    sequence: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Generate the reverse complement of a DNA sequence. Complements each base (A↔T, G↔C) then reverses...

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
            "name": "DNA_reverse_complement",
            "arguments": {"operation": operation, "sequence": sequence},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DNA_reverse_complement"]
