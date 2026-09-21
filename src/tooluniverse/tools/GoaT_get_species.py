"""
GoaT_get_species

Look up genome sequencing status via GoaT (Genomes on a Tree), which indexes the Earth BioGenome ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GoaT_get_species(
    taxon: str,
    include_descendants: Optional[bool] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Look up genome sequencing status via GoaT (Genomes on a Tree), which indexes the Earth BioGenome ...

    Parameters
    ----------
    taxon : str
        Scientific name (e.g. 'Panthera leo') or NCBI taxon id (e.g. '9689').
    include_descendants : bool
        If true and taxon is a numeric id, include all descendant taxa (e.g. every sp...
    limit : int
        Max taxa to return, 1-50. Default 10.
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
            "taxon": taxon,
            "include_descendants": include_descendants,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GoaT_get_species",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GoaT_get_species"]
