"""
PDBe_get_compound_details

Get detailed chemical compound information from the PDBe Graph API by chemical component ID (3-le...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PDBe_get_compound_details(
    comp_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed chemical compound information from the PDBe Graph API by chemical component ID (3-le...

    Parameters
    ----------
    comp_id : str
        Chemical component identifier (3-letter PDB ligand code, uppercase). Examples...
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
        {"name": "PDBe_get_compound_details", "arguments": {"comp_id": comp_id}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PDBe_get_compound_details"]
