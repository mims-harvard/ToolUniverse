"""
KLIFS_get_structures_by_pdb

Get KLIFS kinase structure data for one or more PDB entries by their PDB codes. Returns all kinas...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def KLIFS_get_structures_by_pdb(
    pdb_codes: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get KLIFS kinase structure data for one or more PDB entries by their PDB codes. Returns all kinas...

    Parameters
    ----------
    pdb_codes : str
        Comma-separated list of PDB codes to look up (e.g., '4ekk,3mvh,1iep'). Each m...
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
        {"name": "KLIFS_get_structures_by_pdb", "arguments": {"pdb_codes": pdb_codes}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["KLIFS_get_structures_by_pdb"]
