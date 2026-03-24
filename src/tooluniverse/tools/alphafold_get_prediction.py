"""
alphafold_get_prediction

Retrieve full AlphaFold 3D structure predictions for a given protein. IMPORTANT: The qualifier mu...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def alphafold_get_prediction(
    qualifier: Optional[str] = None,
    uniprot_id: Optional[str] = None,
    uniprot_accession: Optional[str] = None,
    sequence_checksum: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve full AlphaFold 3D structure predictions for a given protein. IMPORTANT: The qualifier mu...

    Parameters
    ----------
    qualifier : str
        UniProt ACCESSION (e.g., 'P69905'). Do NOT use entry names like 'HBA_HUMAN'. ...
    uniprot_id : str
        Alias for qualifier: UniProt accession (e.g., 'P69905').
    uniprot_accession : str
        Alias for qualifier: UniProt accession (e.g., 'P69905').
    sequence_checksum : str
        Optional CRC64 checksum of the UniProt sequence.
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
            "qualifier": qualifier,
            "uniprot_id": uniprot_id,
            "uniprot_accession": uniprot_accession,
            "sequence_checksum": sequence_checksum,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "alphafold_get_prediction",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["alphafold_get_prediction"]
