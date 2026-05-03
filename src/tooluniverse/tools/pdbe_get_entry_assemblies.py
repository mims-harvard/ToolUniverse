"""
pdbe_get_entry_assemblies

Get biological assembly information for a PDB entry including assembly IDs, symmetry operations, ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def pdbe_get_entry_assemblies(
    pdb_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get biological assembly information for a PDB entry including assembly IDs, symmetry operations, ...

    Parameters
    ----------
    pdb_id : str
        PDB entry ID (e.g., '1A2B', '1CRN'). Will be converted to lowercase automatic...
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
    _args = {k: v for k, v in {"pdb_id": pdb_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "pdbe_get_entry_assemblies",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["pdbe_get_entry_assemblies"]
