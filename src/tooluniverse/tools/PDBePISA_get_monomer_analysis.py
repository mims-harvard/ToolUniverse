"""
PDBePISA_get_monomer_analysis

Analyze solvent-accessible surface area and interface participation for each chain in a PDB struc...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PDBePISA_get_monomer_analysis(
    operation: str,
    pdb_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Analyze solvent-accessible surface area and interface participation for each chain in a PDB struc...

    Parameters
    ----------
    operation : str
        Operation type
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

    return get_shared_client().run_one_function(
        {
            "name": "PDBePISA_get_monomer_analysis",
            "arguments": {"operation": operation, "pdb_id": pdb_id},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PDBePISA_get_monomer_analysis"]
