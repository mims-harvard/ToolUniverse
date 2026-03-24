"""
iPTMnet_get_ptm_ppi

Get PTM-dependent protein-protein interactions from iPTMnet. Returns interactions where a post-tr...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def iPTMnet_get_ptm_ppi(
    operation: str,
    uniprot_id: str,
    ptm_type: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get PTM-dependent protein-protein interactions from iPTMnet. Returns interactions where a post-tr...

    Parameters
    ----------
    operation : str
        Operation type
    uniprot_id : str
        UniProt accession, e.g., P04637 (TP53), P00533 (EGFR), P31749 (AKT1)
    ptm_type : str | Any
        Filter by PTM type: Phosphorylation, Acetylation, Ubiquitination, Methylation...
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

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "operation": operation,
            "uniprot_id": uniprot_id,
            "ptm_type": ptm_type,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "iPTMnet_get_ptm_ppi",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["iPTMnet_get_ptm_ppi"]
