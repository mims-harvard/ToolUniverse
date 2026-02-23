"""
miRBase_get_mirna

Get detailed miRNA information from RNAcentral including full RNA sequence, species, RNA type, ge...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def miRBase_get_mirna(
    rnacentral_id: str,
    taxid: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed miRNA information from RNAcentral including full RNA sequence, species, RNA type, ge...

    Parameters
    ----------
    rnacentral_id : str
        RNAcentral URS identifier. Use species-specific format 'URS_TAXID' (e.g., 'UR...
    taxid : int
        NCBI Taxonomy ID for species-specific lookup (e.g., 9606 for human, 10090 for...
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
            "name": "miRBase_get_mirna",
            "arguments": {"rnacentral_id": rnacentral_id, "taxid": taxid},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["miRBase_get_mirna"]
