"""
ZINC_search_by_smiles

Structure-search the ZINC22 (and legacy ZINC20) database by SMILES via the CartBlanche22 async st...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ZINC_search_by_smiles(
    smiles: str,
    operation: Optional[str] = "search_by_smiles",
    dist: Optional[int] = 0,
    adist: Optional[int] = 0,
    database: Optional[str] = "zinc20,zinc22",
    count: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Structure-search the ZINC22 (and legacy ZINC20) database by SMILES via the CartBlanche22 async st...

    Parameters
    ----------
    operation : str
        Operation type
    smiles : str
        SMILES string to search for. Examples: c1ccccc1 (benzene), CC(=O)Oc1ccccc1C(=...
    dist : int
        Graph-edit-distance for similarity search. 0 = exact match; higher = more per...
    adist : int
        Anonymized (atom-type-agnostic) graph-edit-distance. 0 = exact on the anonymi...
    database : str
        Comma-separated databases to search: zinc20, zinc22, or both (default).
    count : int
        Maximum number of results to return (default: 10, max: 100)
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
            "smiles": smiles,
            "dist": dist,
            "adist": adist,
            "database": database,
            "count": count,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ZINC_search_by_smiles",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ZINC_search_by_smiles"]
