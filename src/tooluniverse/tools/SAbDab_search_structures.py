"""
SAbDab_search_structures

Search the current SAbDab2 antibody-structure JSON API. Returns full antibody-instance records pl...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SAbDab_search_structures(
    operation: Optional[str] = "search_structures",
    query: Optional[str] = None,
    antigen: Optional[str] = None,
    limit: Optional[int] = 50,
    offset: Optional[int] = 0,
    pdb_id: Optional[str] = None,
    species: Optional[str] = None,
    resolution_max: Optional[float] = None,
    method: Optional[str] = None,
    antigen_type: Optional[str] = None,
    antibody_type: Optional[str] = None,
    construct_type: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the current SAbDab2 antibody-structure JSON API. Returns full antibody-instance records pl...

    Parameters
    ----------
    operation : str

    query : str
        Bound-antigen name search (e.g., 'SARS-CoV-2' or 'receptor-binding domain'). ...
    antigen : str
        Alias for query. Antigen name to search (e.g., 'EGFR', 'HER2').
    limit : int
        Page size, 1-100 (default: 50).
    offset : int
        Zero-based result offset. Use next_offset from the previous response.
    pdb_id : str
        Restrict to one four-character PDB ID.
    species : str
        Antibody organism scientific name, e.g. 'homo sapiens'.
    resolution_max : float
        Maximum structure resolution in angstroms.
    method : str
        Experimental method, e.g. 'X-ray diffraction'.
    antigen_type : str
        SAbDab2 antigen type filter.
    antibody_type : str
        SAbDab2 antibody type filter, e.g. FAB.
    construct_type : str
        SAbDab2 construct type filter.
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
            "query": query,
            "antigen": antigen,
            "limit": limit,
            "offset": offset,
            "pdb_id": pdb_id,
            "species": species,
            "resolution_max": resolution_max,
            "method": method,
            "antigen_type": antigen_type,
            "antibody_type": antibody_type,
            "construct_type": construct_type,
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
