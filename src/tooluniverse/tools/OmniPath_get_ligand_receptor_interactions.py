"""
OmniPath_get_ligand_receptor_interactions

Get ligand-receptor interaction pairs from OmniPath, the largest integrated intercellular communi...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OmniPath_get_ligand_receptor_interactions(
    partners: Optional[str] = None,
    sources: Optional[str] = None,
    targets: Optional[str] = None,
    databases: Optional[str] = None,
    organisms: Optional[int] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get ligand-receptor interaction pairs from OmniPath, the largest integrated intercellular communi...

    Parameters
    ----------
    partners : str
        Gene symbol(s) or UniProt ID(s) to query as interaction partners (either sour...
    sources : str
        Gene symbol(s) or UniProt ID(s) for source (ligand) proteins only. Use instea...
    targets : str
        Gene symbol(s) or UniProt ID(s) for target (receptor) proteins only. Use inst...
    databases : str
        Filter by specific source database(s), comma-separated. Options include: Cell...
    organisms : int
        NCBI taxonomy ID for species filter. Default: 9606 (human). Options: 9606 (hu...
    limit : int
        Maximum number of interactions to return. Default: no limit (returns all).
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
    _args = {
        k: v
        for k, v in {
            "partners": partners,
            "sources": sources,
            "targets": targets,
            "databases": databases,
            "organisms": organisms,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OmniPath_get_ligand_receptor_interactions",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OmniPath_get_ligand_receptor_interactions"]
