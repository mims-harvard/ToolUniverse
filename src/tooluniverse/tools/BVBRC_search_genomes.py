"""
BVBRC_search_genomes

Search for pathogen genomes in BV-BRC by organism name or keyword, with explicit pagination and o...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BVBRC_search_genomes(
    keyword: str,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    genome_status: Optional[str] = None,
    genome_quality: Optional[str] = None,
    min_checkm_completeness: Optional[float] = None,
    max_checkm_contamination: Optional[float] = None,
    collection_date_start: Optional[str] = None,
    collection_date_end: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search for pathogen genomes in BV-BRC by organism name or keyword, with explicit pagination and o...

    Parameters
    ----------
    keyword : str
        Search keyword - organism name, strain, or pathogen. Examples: 'Staphylococcu...
    limit : int
        Maximum number of results to return per page. Default: 10. Max: 100.
    offset : int
        Zero-based result offset. Use metadata.next_offset to retrieve the next page....
    genome_status : str
        Exact BV-BRC genome status filter, such as 'Complete' or 'WGS'.
    genome_quality : str
        Exact BV-BRC genome quality classification filter, such as 'Good'.
    min_checkm_completeness : float
        Minimum CheckM completeness percentage.
    max_checkm_contamination : float
        Maximum CheckM contamination percentage.
    collection_date_start : str
        Inclusive lower bound for collection_date, in the date format accepted by BV-...
    collection_date_end : str
        Inclusive upper bound for collection_date, in the date format accepted by BV-...
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
            "keyword": keyword,
            "limit": limit,
            "offset": offset,
            "genome_status": genome_status,
            "genome_quality": genome_quality,
            "min_checkm_completeness": min_checkm_completeness,
            "max_checkm_contamination": max_checkm_contamination,
            "collection_date_start": collection_date_start,
            "collection_date_end": collection_date_end,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "BVBRC_search_genomes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BVBRC_search_genomes"]
