"""
BLAST_nucleotide_search

Search nucleotide sequences using NCBI BLAST blastn against nucleotide databases. Requires Biopyt...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BLAST_nucleotide_search(
    sequence: str,
    database: Optional[str] = "nt",
    expect: Optional[float] = 10.0,
    hitlist_size: Optional[int] = 50,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search nucleotide sequences using NCBI BLAST blastn against nucleotide databases. Requires Biopyt...

    Parameters
    ----------
    sequence : str
        DNA sequence to search (minimum 10 nucleotides)
    database : str
        Database to search. Options: 'nt' (comprehensive but slow), 'refseq_select_rn...
    expect : float
        E-value threshold for reporting hits
    hitlist_size : int
        Maximum number of hits to return
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
            "sequence": sequence,
            "database": database,
            "expect": expect,
            "hitlist_size": hitlist_size,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "BLAST_nucleotide_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BLAST_nucleotide_search"]
