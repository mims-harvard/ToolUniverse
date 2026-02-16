"""
PDBe_KB_get_summary_stats

Get aggregated structural summary statistics for a UniProt protein from PDBe-KB. Returns the numb...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PDBe_KB_get_summary_stats(
    uniprot_accession: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get aggregated structural summary statistics for a UniProt protein from PDBe-KB. Returns the numb...

    Parameters
    ----------
    uniprot_accession : str
        UniProt accession ID for the protein. Examples: 'P04637' (TP53), 'P00533' (EG...
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
            "name": "PDBe_KB_get_summary_stats",
            "arguments": {"uniprot_accession": uniprot_accession},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PDBe_KB_get_summary_stats"]
