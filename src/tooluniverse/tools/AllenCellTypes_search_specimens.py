"""
AllenCellTypes_search_specimens

Search Allen Cell Types neuron specimens with exact RMA row pagination. Filter by donor species a...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def AllenCellTypes_search_specimens(
    species: Optional[str] = None,
    structure: Optional[str] = None,
    limit: Optional[int] = 20,
    start_row: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search Allen Cell Types neuron specimens with exact RMA row pagination. Filter by donor species a...

    Parameters
    ----------
    species : str
        Donor species: 'Homo Sapiens' or 'Mus musculus'.
    structure : str
        Brain structure name substring, e.g. 'frontal gyrus', 'visual cortex'.
    limit : int
        Specimens per page (1-2000).
    start_row : int
        Zero-based RMA offset. Continue with metadata.next_start_row.
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
            "species": species,
            "structure": structure,
            "limit": limit,
            "start_row": start_row,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "AllenCellTypes_search_specimens",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["AllenCellTypes_search_specimens"]
