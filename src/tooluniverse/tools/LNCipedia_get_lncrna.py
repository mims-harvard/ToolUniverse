"""
LNCipedia_get_lncrna

Get detailed lncRNA information from RNAcentral including full RNA sequence, species, gene associ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def LNCipedia_get_lncrna(
    rnacentral_id: str,
    taxid: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed lncRNA information from RNAcentral including full RNA sequence, species, gene associ...

    Parameters
    ----------
    rnacentral_id : str
        RNAcentral URS identifier. Use species-specific format 'URS_TAXID' (e.g., 'UR...
    taxid : int
        NCBI Taxonomy ID for species-specific lookup (e.g., 9606 for human). Optional...
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
        for k, v in {"rnacentral_id": rnacentral_id, "taxid": taxid}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "LNCipedia_get_lncrna",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["LNCipedia_get_lncrna"]
