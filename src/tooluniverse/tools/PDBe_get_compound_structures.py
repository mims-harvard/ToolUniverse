"""
PDBe_get_compound_structures

Get PDB structures containing a specific chemical compound (ligand/cofactor/ion). Returns compoun...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PDBe_get_compound_structures(
    comp_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get PDB structures containing a specific chemical compound (ligand/cofactor/ion). Returns compoun...

    Parameters
    ----------
    comp_id : str
        PDB chemical component ID (3-letter code). Examples: 'ATP', 'HEM', 'NAG', 'FA...
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
    _args = {k: v for k, v in {
        "comp_id": comp_id
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "PDBe_get_compound_structures",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["PDBe_get_compound_structures"]
