"""
SASBDB_get_entries_by_uniprot

Find SASBDB small-angle scattering entries associated with a UniProt protein accession. Returns l...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SASBDB_get_entries_by_uniprot(
    uniprot_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Find SASBDB small-angle scattering entries associated with a UniProt protein accession. Returns l...

    Parameters
    ----------
    uniprot_id : str
        UniProt accession (e.g. P00698 for lysozyme, P68871 for hemoglobin)
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    return get_shared_client().run_one_function(
        {
            "name": "SASBDB_get_entries_by_uniprot",
            "arguments": {"uniprot_id": uniprot_id},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SASBDB_get_entries_by_uniprot"]
