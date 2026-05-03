"""
Enamine_search_smiles

Search Enamine by chemical structure (SMILES). Supports exact match, substructure, and similarity...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Enamine_search_smiles(
    smiles: str,
    operation: Optional[str] = None,
    search_type: Optional[str] = "similarity",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search Enamine by chemical structure (SMILES). Supports exact match, substructure, and similarity...

    Parameters
    ----------
    operation : str

    smiles : str
        SMILES string for the query compound
    search_type : str
        Search type: exact, substructure, similarity (default: similarity)
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
            "smiles": smiles,
            "search_type": search_type,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Enamine_search_smiles",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Enamine_search_smiles"]
