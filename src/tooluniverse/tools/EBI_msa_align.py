"""
EBI_msa_align

Multiple sequence alignment (MSA) of user-provided sequences via EMBL-EBI Job Dispatcher. Unlike ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EBI_msa_align(
    sequences: str,
    method: Optional[str] = "clustalo",
    sequence_type: Optional[str] = "protein",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Multiple sequence alignment (MSA) of user-provided sequences via EMBL-EBI Job Dispatcher. Unlike ...

    Parameters
    ----------
    sequences : str
        Two or more sequences in FASTA format (each starting with '>'). Example: '>se...
    method : str
        Alignment program: 'clustalo' (Clustal Omega, default, scales to many sequenc...
    sequence_type : str
        Sequence molecule type: 'protein' (default), 'dna', or 'rna'. Ignored by musc...
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
            "sequences": sequences,
            "method": method,
            "sequence_type": sequence_type,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EBI_msa_align",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EBI_msa_align"]
