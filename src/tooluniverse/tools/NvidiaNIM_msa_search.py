"""
NvidiaNIM_msa_search

GPU-accelerated multiple sequence alignment search using ColabFold/MMseqs2 via NVIDIA NIM. Input:...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NvidiaNIM_msa_search(
    sequence: str,
    e_value: Optional[float] = 0.0001,
    iterations: Optional[int] = 1,
    output_alignment_formats: Optional[list[str]] = None,
    databases: Optional[list[str]] = None,
    max_msa_sequences: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    GPU-accelerated multiple sequence alignment search using ColabFold/MMseqs2 via NVIDIA NIM. Input:...

    Parameters
    ----------
    sequence : str
        Protein sequence to search (1-4096 amino acids)
    e_value : float
        E-value threshold for sequence inclusion
    iterations : int
        Number of search iterations for sensitivity
    output_alignment_formats : list[str]
        Output alignment formats
    databases : list[str]
        Specific databases to search
    max_msa_sequences : int
        Maximum sequences in output MSA (max 10000)
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
    if output_alignment_formats is None:
        output_alignment_formats = ['a3m']
    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {
        "sequence": sequence,
                "e_value": e_value,
                "iterations": iterations,
                "output_alignment_formats": output_alignment_formats,
                "databases": databases,
                "max_msa_sequences": max_msa_sequences
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "NvidiaNIM_msa_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["NvidiaNIM_msa_search"]
