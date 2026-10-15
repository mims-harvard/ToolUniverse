"""
Protein_MSA_inspect

Inspect local single-component protein A3M or aligned FASTA. Reports raw/unique depth, query-only...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Protein_MSA_inspect(
    alignment_path: Optional[str] = None,
    alignment_content: Optional[str] = None,
    format: Optional[str] = None,
    expected_query_sequence: Optional[str] = None,
    max_row_details: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Inspect local single-component protein A3M or aligned FASTA. Reports raw/unique depth, query-only...

    Parameters
    ----------
    alignment_path : str
        Local single-component protein A3M or aligned FASTA path; stays local. Exactl...
    alignment_content : str
        Inline single-component protein A3M or aligned FASTA; stays local. Exactly on...
    format : str
        Default a3m: lowercase residues and dots are insertions. aligned_fasta normal...
    expected_query_sequence : str
        Optional expected ungapped protein sequence, compared to first record. Mismat...
    max_row_details : int
        Bound per-row summaries; default 10. Counts stay complete.
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
            "alignment_path": alignment_path,
            "alignment_content": alignment_content,
            "format": format,
            "expected_query_sequence": expected_query_sequence,
            "max_row_details": max_row_details,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Protein_MSA_inspect",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Protein_MSA_inspect"]
