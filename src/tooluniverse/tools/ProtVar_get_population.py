"""
ProtVar_get_population

Get the known variants at a protein position from ProtVar's population observations: one row per ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ProtVar_get_population(
    accession: str,
    position: int,
    genomic_location: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get the known variants at a protein position from ProtVar's population observations: one row per ...

    Parameters
    ----------
    accession : str
        UniProt accession (e.g. 'P22304' for IDS).
    position : int
        Amino acid position in the protein (1-based).
    genomic_location : int
        Optional genomic coordinate (GRCh38); ProtVar answers for the whole protein p...
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
