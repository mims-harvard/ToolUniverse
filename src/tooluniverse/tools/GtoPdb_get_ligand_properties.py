"""
GtoPdb_get_ligand_properties

Get the chemical structure and computed molecular properties of a ligand from the Guide to Pharma...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GtoPdb_get_ligand_properties(
    ligand_id: Optional[int] = None,
    ligandId: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the chemical structure and computed molecular properties of a ligand from the Guide to Pharma...

    Parameters
    ----------
    ligand_id : int
        GtoPdb ligand ID. Get from GtoPdb_search_ligands. Examples: 4139 (aspirin), 1...
    ligandId : int
        Alias for ligand_id. GtoPdb ligand ID.
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
        for k, v in {"ligand_id": ligand_id, "ligandId": ligandId}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GtoPdb_get_ligand_properties",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GtoPdb_get_ligand_properties"]
