"""
ReMap_get_transcription_factor_binding

Get transcription factor binding sites from ReMap database for specific genes and cell types
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ReMap_get_transcription_factor_binding(
    gene_name: str,
    cell_type: Optional[str] = "HepG2",
    limit: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get transcription factor binding sites from ReMap database for specific genes and cell types

    Parameters
    ----------
    gene_name : str
        Gene symbol (e.g., BRCA1, TP53, MYC)
    cell_type : str
        Cell type (e.g., HepG2, K562, MCF-7)
    limit : int
        Number of results to return
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
            "gene_name": gene_name,
            "cell_type": cell_type,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ReMap_get_transcription_factor_binding",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ReMap_get_transcription_factor_binding"]
