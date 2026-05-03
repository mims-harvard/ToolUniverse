"""
RCSBGraphQL_get_structure_summary

Get comprehensive structure summary for one or more PDB entries using the RCSB PDB Data API (Grap...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def RCSBGraphQL_get_structure_summary(
    pdb_id: Optional[str | Any] = None,
    pdb_ids: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get comprehensive structure summary for one or more PDB entries using the RCSB PDB Data API (Grap...

    Parameters
    ----------
    pdb_id : str | Any
        Single PDB ID. Example: '4HHB' (hemoglobin), '1TUP' (p53-DNA complex), '6LU7'...
    pdb_ids : str | Any
        Comma-separated list of PDB IDs for batch query. Example: '4HHB,1TUP,6LU7'. M...
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
        k: v for k, v in {"pdb_id": pdb_id, "pdb_ids": pdb_ids}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "RCSBGraphQL_get_structure_summary",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["RCSBGraphQL_get_structure_summary"]
