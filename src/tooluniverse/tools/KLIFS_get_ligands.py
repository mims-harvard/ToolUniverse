"""
KLIFS_get_ligands

Get all ligands (co-crystallized inhibitors) bound to a specific kinase across all its crystal st...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def KLIFS_get_ligands(
    kinase_ID: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get all ligands (co-crystallized inhibitors) bound to a specific kinase across all its crystal st...

    Parameters
    ----------
    kinase_ID : int
        KLIFS kinase ID (e.g., 1 for AKT1). Obtain from KLIFS_list_kinases.
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
        {"name": "KLIFS_get_ligands", "arguments": {"kinase_ID": kinase_ID}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["KLIFS_get_ligands"]
