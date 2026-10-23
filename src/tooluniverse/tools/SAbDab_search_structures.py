"""
SAbDab_search_structures

Search SAbDab (Structural Antibody Database) for antibody structures by the antigen they bind, an...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SAbDab_search_structures(
    operation: Optional[str] = "search_structures",
    query: Optional[str] = None,
    antigen: Optional[str] = None,
    limit: Optional[int] = 20,
    species: Optional[str] = None,
    method: Optional[str] = None,
    resolution_max: Optional[float] = None,
    antigen_type: Optional[str] = None,
    antibody_type: Optional[str] = None,
    pdb_id: Optional[str] = None,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search SAbDab (Structural Antibody Database) for antibody structures by the antigen they bind, an...

    Parameters
    ----------
    operation : str

    query : str
        Part of the bound antigen's name as deposited in the PDB, case-insensitive, a...
    antigen : str
        Alias for query.
    limit : int
        Rows per page (1-100, default 20).
    species : str
        Substring of the antibody's source organism scientific name (e.g. 'Homo sapie...
    method : str
        Experimental method of the structure (case-insensitive).
    resolution_max : float
        Keep structures determined at this resolution (angstroms) or better.
    antigen_type : str
        Kind of antigen bound (case-insensitive).
    antibody_type : str
        Antibody format: FV, FAB, FAB+FC, FV*, SD-H (heavy-chain single domain, e.g. ...
    pdb_id : str
        Restrict to one PDB entry (4-character code, e.g. '3hfm').
    offset : int
        Zero-based row offset; continue with data.next_offset while data.has_more is ...
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
            "operation": operation,
            "query": query,
            "antigen": antigen,
            "limit": limit,
            "species": species,
            "method": method,
            "resolution_max": resolution_max,
            "antigen_type": antigen_type,
            "antibody_type": antibody_type,
            "pdb_id": pdb_id,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "SAbDab_search_structures",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SAbDab_search_structures"]
