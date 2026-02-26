"""
GTDB_get_genome

Get comprehensive metadata for a specific genome by NCBI accession from GTDB. Returns nucleotide ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GTDB_get_genome(
    operation: str,
    accession: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get comprehensive metadata for a specific genome by NCBI accession from GTDB. Returns nucleotide ...

    Parameters
    ----------
    operation : str
        Operation type (fixed: get_genome)
    accession : str
        NCBI genome accession (e.g., 'GCF_000005845.2' for E. coli K-12, 'GCF_0000090...
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
            "name": "GTDB_get_genome",
            "arguments": {"operation": operation, "accession": accession},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GTDB_get_genome"]
