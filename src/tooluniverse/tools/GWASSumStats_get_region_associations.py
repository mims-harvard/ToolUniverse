"""
GWASSumStats_get_region_associations

Query full GWAS summary statistics for variants in a chromosomal region. Returns variant-level as...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GWASSumStats_get_region_associations(
    chromosome: int,
    bp_lower: int,
    bp_upper: int,
    p_upper: Optional[float | Any] = None,
    study_accession: Optional[str | Any] = None,
    size: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Query full GWAS summary statistics for variants in a chromosomal region. Returns variant-level as...

    Parameters
    ----------
    chromosome : int
        Chromosome number (1-22, or 23 for X).
    bp_lower : int
        Start position of the region (GRCh38 coordinates).
    bp_upper : int
        End position of the region (GRCh38 coordinates).
    p_upper : float | Any
        Maximum p-value threshold (default 5e-8 for genome-wide significance). Use la...
    study_accession : str | Any
        Filter by specific GWAS study accession (e.g., 'GCST002245'). Get study IDs f...
    size : int | Any
        Maximum number of variants to return (default 50, max 1000).
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
            "chromosome": chromosome,
            "bp_lower": bp_lower,
            "bp_upper": bp_upper,
            "p_upper": p_upper,
            "study_accession": study_accession,
            "size": size,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GWASSumStats_get_region_associations",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GWASSumStats_get_region_associations"]
