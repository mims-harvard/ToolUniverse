"""
EBI_pairwise_align

Align exactly two sequences via EMBL-EBI EMBOSS and return the alignment with percent identity, s...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EBI_pairwise_align(
    sequence_a: str,
    sequence_b: str,
    algorithm: Optional[str] = None,
    sequence_type: Optional[str] = None,
    matrix: Optional[str] = None,
    gap_open: Optional[float] = None,
    gap_extend: Optional[float] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Align exactly two sequences via EMBL-EBI EMBOSS and return the alignment with percent identity, s...

    Parameters
    ----------
    sequence_a : str
        First sequence, FASTA or raw.
    sequence_b : str
        Second sequence, FASTA or raw.
    algorithm : str
        'needle' (global, default), 'stretcher' (global, long sequences), or 'matcher...
    sequence_type : str
        'protein' (default) or 'dna'.
    matrix : str
        Scoring matrix, e.g. 'EBLOSUM62' for protein or 'EDNAFULL' for DNA.
    gap_open : float
        Gap opening penalty.
    gap_extend : float
        Gap extension penalty.
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
            "sequence_a": sequence_a,
            "sequence_b": sequence_b,
            "algorithm": algorithm,
            "sequence_type": sequence_type,
            "matrix": matrix,
            "gap_open": gap_open,
            "gap_extend": gap_extend,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EBI_pairwise_align",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EBI_pairwise_align"]
