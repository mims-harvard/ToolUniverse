"""
Foldseek_search_structure

Search for structurally similar proteins using Foldseek. Given a PDB ID, downloads the structure ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Foldseek_search_structure(
    pdb_id: Optional[str] = None,
    sequence: Optional[str] = None,
    query: Optional[str] = None,
    database: Optional[str] = "afdb50",
    mode: Optional[str] = "3diaa",
    max_results: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search for structurally similar proteins using Foldseek. Given a PDB ID, downloads the structure ...

    Parameters
    ----------
    pdb_id : str
        PDB ID to search (e.g., '4HHB', '1CRN'). The structure will be fetched from R...
    sequence : str
        Amino acid sequence to search (alternative to pdb_id). For sequence-based str...
    query : str
        Amino acid sequence to search (alias for sequence).
    database : str
        Database to search against. Options: 'afdb50' (AlphaFold DB 50% clustered, de...
    mode : str
        Search mode: 'tmalign' (fast 3Di+AA, default), 'tmalign' (TM-align, slower bu...
    max_results : int
        Maximum number of results to return (default 10, max 50).
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
            "pdb_id": pdb_id,
            "sequence": sequence,
            "query": query,
            "database": database,
            "mode": mode,
            "max_results": max_results,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Foldseek_search_structure",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Foldseek_search_structure"]
