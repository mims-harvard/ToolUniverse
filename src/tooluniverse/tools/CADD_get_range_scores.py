"""
CADD_get_range_scores

Get CADD scores for all variants in a genomic range (max 100bp). Returns all pre-computed deleter...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CADD_get_range_scores(
    chrom: str,
    start: int,
    end: int,
    version: Optional[str] = "GRCh38-v1.7",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get CADD scores for all variants in a genomic range (max 100bp). Returns all pre-computed deleter...

    Parameters
    ----------
    chrom : str
        Chromosome (1-22, X, Y, MT)
    start : int
        Start position (1-based, inclusive)
    end : int
        End position (1-based, inclusive). Max range: 100bp.
    version : str
        CADD version and genome build
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
            "chrom": chrom,
            "start": start,
            "end": end,
            "version": version,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "CADD_get_range_scores",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CADD_get_range_scores"]
