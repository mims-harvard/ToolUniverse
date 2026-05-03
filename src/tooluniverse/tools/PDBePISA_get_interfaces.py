"""
PDBePISA_get_interfaces

Analyze protein-protein and protein-ligand interfaces in a crystal structure using PDBePISA. Retu...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PDBePISA_get_interfaces(
    pdb_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Analyze protein-protein and protein-ligand interfaces in a crystal structure using PDBePISA. Retu...

    Parameters
    ----------
    pdb_id : str
        PDB entry ID (4-character code, e.g., '4hhb' for hemoglobin, '1cbs' for CRABP...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {"pdb_id": pdb_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "PDBePISA_get_interfaces",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PDBePISA_get_interfaces"]
