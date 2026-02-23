"""
GtoPdb_get_interactions

Get pharmacological interactions between targets and ligands from the Guide to Pharmacology datab...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GtoPdb_get_interactions(
    targetId: Optional[int | Any] = None,
    ligandId: Optional[int | Any] = None,
    species: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get pharmacological interactions between targets and ligands from the Guide to Pharmacology datab...

    Parameters
    ----------
    targetId : int | Any
        GtoPdb target ID. Get from GtoPdb_search_targets. Examples: 2486 (dopamine be...
    ligandId : int | Any
        GtoPdb ligand ID. Get from GtoPdb_search_ligands. Examples: 5765 (aspirin), 7...
    species : str | Any
        Filter by species. Examples: 'Human', 'Mouse', 'Rat'
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
            "name": "GtoPdb_get_interactions",
            "arguments": {
                "targetId": targetId,
                "ligandId": ligandId,
                "species": species,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GtoPdb_get_interactions"]
