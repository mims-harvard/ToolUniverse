"""
RCSBData_get_assembly

Get biological assembly details for a PDB structure from the RCSB Data API. Returns oligomeric st...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def RCSBData_get_assembly(
    pdb_id: str,
    assembly_id: Optional[str] = "1",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get biological assembly details for a PDB structure from the RCSB Data API. Returns oligomeric st...

    Parameters
    ----------
    pdb_id : str
        PDB entry ID (4 characters). Examples: '4HHB' (hemoglobin tetramer), '1TUP' (...
    assembly_id : str
        Assembly identifier (default '1' for the first/preferred assembly). Most stru...
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

    return get_shared_client().run_one_function(
        {
            "name": "RCSBData_get_assembly",
            "arguments": {"pdb_id": pdb_id, "assembly_id": assembly_id},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["RCSBData_get_assembly"]
