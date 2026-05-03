"""
ENCODE_search_experiments

Search ENCODE functional genomics experiments (e.g., ChIP-seq, ATAC-seq, RNA-seq) by assay type, ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ENCODE_search_experiments(
    assay_title: Optional[str] = None,
    target: Optional[str] = None,
    organism: Optional[str] = None,
    status: Optional[str] = "released",
    limit: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search ENCODE functional genomics experiments (e.g., ChIP-seq, ATAC-seq, RNA-seq) by assay type, ...

    Parameters
    ----------
    assay_title : str
        Assay name filter (e.g., 'TF ChIP-seq', 'Histone ChIP-seq', 'ATAC-seq', 'RNA-...
    target : str
        Target protein/factor filter (e.g., 'CTCF', 'H3K4me3', 'POLR2A'). Use for TF ...
    organism : str
        Organism filter — maps to ENCODE's organism scientific name field (e.g., 'Hom...
    status : str
        Record status filter. Use 'released' for public data (default), 'archived' fo...
    limit : int
        Maximum number of results to return (1–100).
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
            "assay_title": assay_title,
            "target": target,
            "organism": organism,
            "status": status,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ENCODE_search_experiments",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ENCODE_search_experiments"]
