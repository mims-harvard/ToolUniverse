"""
PubChem_search_compounds_by_substructure

Search for CIDs in PubChem that contain the given substructure (SMILES). Returns up to max_result...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PubChem_search_compounds_by_substructure(
    smiles: str,
    max_results: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search for CIDs in PubChem that contain the given substructure (SMILES). Returns up to max_result...

    Parameters
    ----------
    smiles : str
        SMILES of substructure (e.g., "c1ccccc1" corresponds to benzene ring).
    max_results : int
        Maximum number of CIDs to return (default: 10, max: 10000).
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
        for k, v in {"smiles": smiles, "max_results": max_results}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PubChem_search_compounds_by_substructure",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PubChem_search_compounds_by_substructure"]
