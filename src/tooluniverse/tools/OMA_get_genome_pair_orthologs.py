"""
OMA_get_genome_pair_orthologs

Retrieve pairwise orthologs between two whole genomes in OMA. Unlike OMA_get_orthologs, this endp...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OMA_get_genome_pair_orthologs(
    genome1: str,
    genome2: str,
    per_page: Optional[int] = None,
    page: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve pairwise orthologs between two whole genomes in OMA. Unlike OMA_get_orthologs, this endp...

    Parameters
    ----------
    genome1 : str
        First genome: UniProt species code (e.g. 'HUMAN', 'PANTR') or NCBI taxon ID (...
    genome2 : str
        Second genome: UniProt species code (e.g. 'MOUSE', 'PANTR') or NCBI taxon ID ...
    per_page : int
        Ortholog pairs per official server page (default 20, verified through 10000)....
    page : int
        One-based official result page (default 1). Continue with metadata.next_page ...
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
            "genome1": genome1,
            "genome2": genome2,
            "per_page": per_page,
            "page": page,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OMA_get_genome_pair_orthologs",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OMA_get_genome_pair_orthologs"]
