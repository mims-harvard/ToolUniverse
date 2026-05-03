"""
ChEMBL_search_molecules

Search molecules by name, ChEMBL ID, or other criteria. Supports filtering and pagination. Note: ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ChEMBL_search_molecules(
    molecule_chembl_id: Optional[str] = None,
    pref_name__contains: Optional[str] = None,
    query: Optional[str] = None,
    max_results: Optional[int] = 20,
    molecule_type: Optional[str] = None,
    fields: Optional[list[str]] = None,
    limit: Optional[int] = 20,
    offset: Optional[int] = 0,
    format: Optional[str] = "json",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search molecules by name, ChEMBL ID, or other criteria. Supports filtering and pagination. Note: ...

    Parameters
    ----------
    molecule_chembl_id : str
        Filter by ChEMBL ID (exact match)
    pref_name__contains : str
        Filter by preferred name (contains). Note: `pref_name` coverage is incomplete...
    query : str
        Molecule name to search for. Alias for pref_name__contains.
    max_results : int
        Maximum number of results to return. Alias for limit.
    molecule_type : str
        Filter by molecule type (e.g., 'Small molecule', 'Antibody')
    fields : list[str]
        Optional list of ChEMBL molecule fields to include in each returned molecule ...
    limit : int
        Maximum number of results (default: 20, max: 1000)
    offset : int
        Offset for pagination (default: 0)
    format : str

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
            "molecule_chembl_id": molecule_chembl_id,
            "pref_name__contains": pref_name__contains,
            "query": query,
            "max_results": max_results,
            "molecule_type": molecule_type,
            "fields": fields,
            "limit": limit,
            "offset": offset,
            "format": format,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ChEMBL_search_molecules",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ChEMBL_search_molecules"]
