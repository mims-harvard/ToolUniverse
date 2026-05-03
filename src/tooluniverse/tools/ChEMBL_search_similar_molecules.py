"""
ChEMBL_search_similar_molecules

Search for molecules similar to a given SMILES, chembl_id, or compound or drug name, using the Ch...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ChEMBL_search_similar_molecules(
    query: str,
    similarity_threshold: int,
    max_results: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search for molecules similar to a given SMILES, chembl_id, or compound or drug name, using the Ch...

    Parameters
    ----------
    query : str
        SMILES string, chembl_id, or compound or drug name. Note: Only small molecule...
    similarity_threshold : int
        Similarity threshold (0–100).
    max_results : int
        Maximum number of results to return.
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "query": query,
            "similarity_threshold": similarity_threshold,
            "max_results": max_results,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ChEMBL_search_similar_molecules",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ChEMBL_search_similar_molecules"]
