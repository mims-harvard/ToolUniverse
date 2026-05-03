"""
civic_search_molecular_profiles

Search for molecular profiles in CIViC database. Molecular profiles represent combinations of var...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def civic_search_molecular_profiles(
    limit: Optional[int] = 20,
    query: Optional[str] = None,
    name: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search for molecular profiles in CIViC database. Molecular profiles represent combinations of var...

    Parameters
    ----------
    limit : int
        Maximum number of molecular profiles to return (default: 20, recommended max:...
    query : str
        Filter by molecular profile name (e.g., 'BRAF V600E', 'EGFR T790M', 'FLT3 ITD...
    name : str
        Alias for query. Filter by molecular profile name (e.g., 'PD-L1', 'KRAS G12C').
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
        for k, v in {"limit": limit, "query": query, "name": name}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "civic_search_molecular_profiles",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["civic_search_molecular_profiles"]
