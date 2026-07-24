"""
RNAcentral_get_region_ncRNAs

List all RNAcentral non-coding RNAs overlapping a genome locus, aggregated from 50+ member databa...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def RNAcentral_get_region_ncRNAs(
    region: Optional[str] = None,
    species: Optional[str] = None,
    chromosome: Optional[str] = None,
    start: Optional[int] = None,
    end: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List all RNAcentral non-coding RNAs overlapping a genome locus, aggregated from 50+ member databa...

    Parameters
    ----------
    region : str
        Locus as 'chr:start-end' (1-based), e.g. '2:39745816-39826679'. Omit if givin...
    species : str
        Ensembl species slug (default 'homo_sapiens'). E.g. 'mus_musculus', 'danio_re...
    chromosome : str
        Chromosome name without 'chr' prefix, e.g. '2'. Used with start/end when 'reg...
    start : int
        Region start (1-based). Used with chromosome/end when 'region' is omitted.
    end : int
        Region end (1-based). Used with chromosome/start when 'region' is omitted.
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
            "region": region,
            "species": species,
            "chromosome": chromosome,
            "start": start,
            "end": end,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "RNAcentral_get_region_ncRNAs",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["RNAcentral_get_region_ncRNAs"]
