"""
RCSBGraphQL_get_polymer_entity

Get detailed polymer entity information from PDB structures including amino acid sequence, chain ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def RCSBGraphQL_get_polymer_entity(
    pdb_id: Optional[str | Any] = None,
    entity_num: Optional[int | Any] = None,
    entity_ids: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed polymer entity information from PDB structures including amino acid sequence, chain ...

    Parameters
    ----------
    pdb_id : str | Any
        PDB ID (will fetch entity 1 by default). Examples: '4HHB' (hemoglobin), '1TUP...
    entity_num : int | Any
        Entity number within the PDB entry (default: 1). PDB entries can have multipl...
    entity_ids : str | Any
        Comma-separated list of entity IDs for batch query. Format: 'PDB_ENTITY' (e.g...
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
            "entity_num": entity_num,
            "entity_ids": entity_ids,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "RCSBGraphQL_get_polymer_entity",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["RCSBGraphQL_get_polymer_entity"]
