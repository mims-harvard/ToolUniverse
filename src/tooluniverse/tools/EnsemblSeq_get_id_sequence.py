"""
EnsemblSeq_get_id_sequence

Get the amino acid or nucleotide sequence for an Ensembl protein, transcript, or gene ID with rec...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EnsemblSeq_get_id_sequence(
    ensembl_id: str,
    type_: Optional[str] = None,
    max_length: Optional[int] = 10000,
    sequence_offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the amino acid or nucleotide sequence for an Ensembl protein, transcript, or gene ID with rec...

    Parameters
    ----------
    ensembl_id : str
        Ensembl stable ID. Examples: 'ENSP00000269305' (TP53 protein, 393 aa), 'ENST0...
    type_ : str
        Sequence type. If omitted: protein for ENSP, cDNA for ENST, genomic for ENSG/...
    max_length : int
        Maximum sequence characters in this page.
    sequence_offset : int
        Zero-based sequence characters to skip. Continue with next_sequence_offset.
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
            "ensembl_id": ensembl_id,
            "type": type_,
            "max_length": max_length,
            "sequence_offset": sequence_offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EnsemblSeq_get_id_sequence",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EnsemblSeq_get_id_sequence"]
