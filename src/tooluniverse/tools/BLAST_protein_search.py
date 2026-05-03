"""
BLAST_protein_search

Search protein sequences using NCBI BLAST blastp against protein databases. Requires Biopython (p...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BLAST_protein_search(
    sequence: str,
    database: Optional[str] = "nr",
    expect: Optional[float] = 10.0,
    hitlist_size: Optional[int] = 50,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search protein sequences using NCBI BLAST blastp against protein databases. Requires Biopython (p...

    Parameters
    ----------
    sequence : str
        Protein sequence to search (minimum 10 amino acids)
    database : str
        Database to search. Options: 'nr' (comprehensive but slow), 'swissprot' (cura...
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
            "name": "BLAST_protein_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BLAST_protein_search"]
