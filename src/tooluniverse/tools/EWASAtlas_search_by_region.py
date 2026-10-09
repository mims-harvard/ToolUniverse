"""
EWASAtlas_search_by_region

List the CpG probes with curated epigenome-wide association study (EWAS) results inside a genomic...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EWASAtlas_search_by_region(
    chromosome: str,
    start: int,
    end: int,
    limit: Optional[int] = None,
    max_associations_per_probe: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    List the CpG probes with curated epigenome-wide association study (EWAS) results inside a genomic...

    Parameters
    ----------
    chromosome : str
        Chromosome: 1-22, X or Y ('chr' prefix accepted).
    start : int
        Window start, GRCh37/hg19, 1-based.
    end : int
        Window end, GRCh37/hg19. end - start must be at most 1,000,000.
    limit : int
        Max probes to return, 1-500. Default 50.
    max_associations_per_probe : int
        Max associations listed under each probe, 1-200. Default 10 (association_coun...
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
            "start": start,
            "end": end,
            "limit": limit,
            "max_associations_per_probe": max_associations_per_probe,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EWASAtlas_search_by_region",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EWASAtlas_search_by_region"]
