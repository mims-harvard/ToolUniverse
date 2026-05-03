"""
BVBRC_get_protein_structure

Get detailed pathogen protein structure information from BV-BRC by PDB ID. Returns structure meta...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BVBRC_get_protein_structure(
    pdb_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed pathogen protein structure information from BV-BRC by PDB ID. Returns structure meta...

    Parameters
    ----------
    pdb_id : str
        PDB identifier for the protein structure. Examples: '6VSB' (SARS-CoV-2 spike)...
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
    _args = {k: v for k, v in {"pdb_id": pdb_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "BVBRC_get_protein_structure",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BVBRC_get_protein_structure"]
