"""
RCSBGraphQL_get_ligand_info

Get detailed chemical component (ligand) information from the PDB using the RCSB Data API. Return...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def RCSBGraphQL_get_ligand_info(
    comp_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed chemical component (ligand) information from the PDB using the RCSB Data API. Return...

    Parameters
    ----------
    comp_id : str
        PDB chemical component identifier (3-letter code). Examples: 'ATP' (adenosine...
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
        {"name": "RCSBGraphQL_get_ligand_info", "arguments": {"comp_id": comp_id}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["RCSBGraphQL_get_ligand_info"]
