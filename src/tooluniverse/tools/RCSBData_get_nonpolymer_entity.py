"""
RCSBData_get_nonpolymer_entity

Get non-polymer entity (ligand/small molecule) details from a PDB structure via the RCSB Data API...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def RCSBData_get_nonpolymer_entity(
    pdb_id: str,
    entity_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get non-polymer entity (ligand/small molecule) details from a PDB structure via the RCSB Data API...

    Parameters
    ----------
    pdb_id : str
        PDB entry ID (4 characters). Examples: '4HHB' (hemoglobin + heme), '3ERT' (es...
    entity_id : str
        Entity ID within the PDB entry. Non-polymer entities typically start after th...
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
        "pdb_id": pdb_id,
                "entity_id": entity_id
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "RCSBData_get_nonpolymer_entity",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["RCSBData_get_nonpolymer_entity"]
