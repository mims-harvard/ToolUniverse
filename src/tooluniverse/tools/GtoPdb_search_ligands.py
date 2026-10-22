"""
GtoPdb_search_ligands

Search the Guide to Pharmacology database for pharmacological ligands with recoverable local offs...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GtoPdb_search_ligands(
    name: Optional[str] = None,
    type_: Optional[str] = None,
    approved: Optional[bool] = None,
    query: Optional[str] = None,
    limit: Optional[int] = 50,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the Guide to Pharmacology database for pharmacological ligands with recoverable local offs...

    Parameters
    ----------
    name : str
        Ligand name or INN to search. Examples: 'aspirin', 'morphine', 'dopamine', 'c...
    type_ : str
        Ligand type filter. Values: 'Approved', 'Synthetic organic', 'Natural product...
    approved : bool
        Filter to approved drugs only (true) or all ligands (false/omit)
    query : str
        Name/keyword to search for. Alias for the "name" parameter.
    limit : int
        Number of ligands on this page (1-1000; default 50).
    offset : int
        Zero-based ligand offset. Continue with next_offset while has_more is true.
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
            "name": name,
            "type": type_,
            "approved": approved,
            "query": query,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GtoPdb_search_ligands",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GtoPdb_search_ligands"]
