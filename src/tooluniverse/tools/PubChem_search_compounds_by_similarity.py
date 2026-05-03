"""
PubChem_search_compounds_by_similarity

Search by similarity (Tanimoto coefficient), returns CID list of compounds with similarity above ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PubChem_search_compounds_by_similarity(
    smiles: str,
    threshold: float,
    max_results: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search by similarity (Tanimoto coefficient), returns CID list of compounds with similarity above ...

    Parameters
    ----------
    smiles : str
        SMILES expression of target molecule.
    threshold : float
        Similarity threshold (between 0 and 1), e.g., 0.9 means 90% similarity.
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
        for k, v in {
            "smiles": smiles,
            "threshold": threshold,
            "max_results": max_results,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PubChem_search_compounds_by_similarity",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PubChem_search_compounds_by_similarity"]
