"""
GPCRdb_get_structures

Get GPCR crystal/cryo-EM structures from GPCRdb. Returns PDB codes, resolution, receptor state (a...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GPCRdb_get_structures(
    operation: Optional[str] = None,
    protein: Optional[str] = None,
    state: Optional[str] = None,
    resolution: Optional[float] = None,
    protein_id: Optional[str] = None,
    receptor_name: Optional[str] = None,
    protein_name: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get GPCR crystal/cryo-EM structures from GPCRdb. Returns PDB codes, resolution, receptor state (a...

    Parameters
    ----------
    operation : str
        Operation type (fixed: get_structures)
    protein : str
        Protein entry name (optional - returns all structures if not specified)
    state : str
        Receptor state filter: active, inactive, intermediate
    resolution : float
        Maximum resolution in Angstroms (client-side filter, e.g., 2.5 returns only s...
    protein_id : str
        Alias for protein parameter
    receptor_name : str
        Alias for protein. GPCRdb entry name (e.g., adrb2_human).
    protein_name : str
        Alias for protein. GPCRdb entry name (e.g., adrb2_human).
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
    _args = {
        k: v
        for k, v in {
            "operation": operation,
            "protein": protein,
            "state": state,
            "resolution": resolution,
            "protein_id": protein_id,
            "receptor_name": receptor_name,
            "protein_name": protein_name,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GPCRdb_get_structures",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GPCRdb_get_structures"]
