"""
DNA_find_orfs

Find open reading frames (ORFs) in a DNA sequence by scanning for ATG start codons followed by st...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DNA_find_orfs(
    operation: str,
    sequence: str,
    min_length: Optional[int] = 100,
    strand: Optional[str | Any] = "both",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Find open reading frames (ORFs) in a DNA sequence by scanning for ATG start codons followed by st...

    Parameters
    ----------
    operation : str
        Operation type
    sequence : str
        DNA sequence (A, T, G, C, N only)
    min_length : int
        Minimum ORF length in nucleotides (default: 100 nt = ~33 amino acids)
    strand : str | Any
        Which strand to search: 'forward', 'reverse', or 'both' (default)
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
    _args = {
        k: v
        for k, v in {
            "operation": operation,
            "sequence": sequence,
            "min_length": min_length,
            "strand": strand,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "DNA_find_orfs",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DNA_find_orfs"]
