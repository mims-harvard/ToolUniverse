"""
ProteinsPlus_protonate_structure

Add hydrogens and optimize protonation with ProtoSS. Accept exactly one PDB ID or raw PDB text. C...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ProteinsPlus_protonate_structure(
    pdb_id: Optional[str] = None,
    pdb_content: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Add hydrogens and optimize protonation with ProtoSS. Accept exactly one PDB ID or raw PDB text. C...

    Parameters
    ----------
    pdb_id : str
        PDB identifier (e.g., '1cbs', '1KZK', '4HHB'). Use either pdb_id or pdb_conte...
    pdb_content : str
        Raw PDB file content as a string (multi-line text). Use either pdb_id or pdb_...
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
        for k, v in {"pdb_id": pdb_id, "pdb_content": pdb_content}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ProteinsPlus_protonate_structure",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ProteinsPlus_protonate_structure"]
