"""
Sequence_count_residues

Count occurrences of a specific amino acid or nucleotide residue in a sequence. Accepts either a ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Sequence_count_residues(
    residue: str,
    operation: Optional[str] = "count_residues",
    sequence: Optional[str] = None,
    uniprot_id: Optional[str] = None,
    position_limit: Optional[int] = 50,
    position_offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Count occurrences of a specific amino acid or nucleotide residue in a sequence. Accepts either a ...

    Parameters
    ----------
    operation : str
        Operation type
    sequence : str
        Sequence string (DNA/RNA/protein). Optional if uniprot_id is provided.
    uniprot_id : str
        UniProt accession to fetch sequence from (e.g., 'P00533' for EGFR). Optional ...
    residue : str
        Single character residue to count (e.g., 'C' for cysteine)
    position_limit : int
        Maximum number of matching 1-based residue positions to return on this page.
    position_offset : int
        Zero-based offset into all matching residue positions. Continue with data.nex...
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
            "operation": operation,
            "sequence": sequence,
            "uniprot_id": uniprot_id,
            "residue": residue,
            "position_limit": position_limit,
            "position_offset": position_offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Sequence_count_residues",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Sequence_count_residues"]
