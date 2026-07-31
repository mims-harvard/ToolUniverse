"""
Sequence_dn_ds

Compute dN/dS (Ka/Ks) between two coding sequences via the Nei-Gojobori (1986) estimator with Juk...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Sequence_dn_ds(
    seq1: Optional[str] = None,
    seq2: Optional[str] = None,
    fasta1_path: Optional[str] = None,
    fasta2_path: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Compute dN/dS (Ka/Ks) between two coding sequences via the Nei-Gojobori (1986) estimator with Juk...

    Parameters
    ----------
    seq1 : str
        First coding sequence (in-frame, codon-aligned to seq2). DNA/RNA letters.
    seq2 : str
        Second coding sequence (same length/frame as seq1).
    fasta1_path : str
        Alternative to seq1: path to a single-record FASTA
    fasta2_path : str
        Alternative to seq2: path to a single-record FASTA
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
            "seq1": seq1,
            "seq2": seq2,
            "fasta1_path": fasta1_path,
            "fasta2_path": fasta2_path,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Sequence_dn_ds",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Sequence_dn_ds"]
