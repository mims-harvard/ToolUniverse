"""
SKEMPI_search_by_structure

List every experimentally measured binding-affinity mutation for a protein-protein complex in SKE...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SKEMPI_search_by_structure(
    pdb_id: str,
    only_single_mutants: Optional[bool] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List every experimentally measured binding-affinity mutation for a protein-protein complex in SKE...

    Parameters
    ----------
    pdb_id : str
        PDB entry of the complex, e.g. '1CSE' or '1VFB'.
    only_single_mutants : bool
        If true, exclude records carrying more than one substitution.
    limit : int
        Maximum records to return (default 50, max 500).
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
            "pdb_id": pdb_id,
            "only_single_mutants": only_single_mutants,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "SKEMPI_search_by_structure",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SKEMPI_search_by_structure"]
