"""
ProtVar_get_population

Get population observation data for a protein variant position from ProtVar. Returns co-located v...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ProtVar_get_population(
    accession: str,
    position: int,
    genomic_location: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get population observation data for a protein variant position from ProtVar. Returns co-located v...

    Parameters
    ----------
    accession : str
        UniProt accession (e.g. 'P22304' for IDS).
    position : int
        Amino acid position in the protein (1-based).
    genomic_location : int
        Genomic coordinate (GRCh38) for the variant. Obtain from ProtVar_map_variant ...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "accession": accession,
            "position": position,
            "genomic_location": genomic_location,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ProtVar_get_population",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ProtVar_get_population"]
