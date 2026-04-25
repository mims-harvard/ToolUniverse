"""
MEME_tomtom_compare

Compare a query motif against known motif databases (JASPAR, HOCOMOCO, CIS-BP) using TOMTOM from ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MEME_tomtom_compare(
    operation: str,
    query_motif: str,
    target_db: Optional[str | Any] = 'JASPAR2026_vertebrates',
    evalue_threshold: Optional[float | Any] = 0.5,
    comparison_function: Optional[str | Any] = 'pearson',
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Compare a query motif against known motif databases (JASPAR, HOCOMOCO, CIS-BP) using TOMTOM from ...

    Parameters
    ----------
    operation : str
        Operation type
    query_motif : str
        Query motif in MEME format. Must include the full MEME header followed by one...
    target_db : str | Any
        Target motif database to search against. Options: 'JASPAR2026_vertebrates' (d...
    evalue_threshold : float | Any
        E-value threshold for reporting matches. Default 0.5. Must be <= 1.0.
    comparison_function : str | Any
        Distance function for motif comparison. 'pearson' = Pearson correlation (defa...
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
    _args = {k: v for k, v in {
        "operation": operation,
                "query_motif": query_motif,
                "target_db": target_db,
                "evalue_threshold": evalue_threshold,
                "comparison_function": comparison_function
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "MEME_tomtom_compare",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["MEME_tomtom_compare"]
