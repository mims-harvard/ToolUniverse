"""
GTDB_get_species

Get a recoverable page of genomes in a GTDB species cluster. total_genomes is exact because GTDB ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GTDB_get_species(
    species: str,
    operation: Optional[str] = "get_species",
    max_genomes: Optional[int] = None,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get a recoverable page of genomes in a GTDB species cluster. total_genomes is exact because GTDB ...

    Parameters
    ----------
    operation : str
        Operation type (fixed: get_species)
    species : str
        Species name WITHOUT the s__ prefix (e.g., 'Escherichia coli', 'Hydrogenother...
    max_genomes : int
        Maximum number of genomes to return (default: 20). Species clusters can have ...
    offset : int
        Zero-based genome offset. Continue with next_offset.
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
            "operation": operation,
            "species": species,
            "max_genomes": max_genomes,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GTDB_get_species",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GTDB_get_species"]
