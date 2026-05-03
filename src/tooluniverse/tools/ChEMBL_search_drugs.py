"""
ChEMBL_search_drugs

Search drugs by name, approval status, or other criteria. Use the `query` parameter to search by ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ChEMBL_search_drugs(
    query: Optional[str] = None,
    max_phase: Optional[int] = None,
    limit: Optional[int] = 20,
    offset: Optional[int] = 0,
    molecule_chembl_id: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search drugs by name, approval status, or other criteria. Use the `query` parameter to search by ...

    Parameters
    ----------
    query : str
        Drug name to search for (partial match, case-insensitive). E.g., "sotorasib",...
    max_phase : int
        Filter by maximum development phase (0-4)
    limit : int

    offset : int

    molecule_chembl_id : str
        Filter by ChEMBL molecule ID (e.g., "CHEMBL1201581" for adalimumab).
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
            "query": query,
            "max_phase": max_phase,
            "limit": limit,
            "offset": offset,
            "molecule_chembl_id": molecule_chembl_id,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ChEMBL_search_drugs",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ChEMBL_search_drugs"]
