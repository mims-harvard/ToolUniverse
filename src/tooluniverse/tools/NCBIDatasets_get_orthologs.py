"""
NCBIDatasets_get_orthologs

Get orthologous genes across species for a given NCBI Gene ID. NCBI's ortholog endpoint returns a...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NCBIDatasets_get_orthologs(
    gene_id: str,
    page_size: Optional[int] = None,
    offset: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get orthologous genes across species for a given NCBI Gene ID. NCBI's ortholog endpoint returns a...

    Parameters
    ----------
    gene_id : str
        NCBI Gene ID (numeric). Examples: '7157' (TP53), '672' (BRCA1), '3630' (INS).
    page_size : int
        Maximum orthologs in this local result page (1-1000, default 20).
    offset : int
        Zero-based offset into the complete ortholog set (default 0). Use metadata.ne...
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
            "gene_id": gene_id,
            "page_size": page_size,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "NCBIDatasets_get_orthologs",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NCBIDatasets_get_orthologs"]
