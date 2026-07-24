"""
EBIProteins_get_proteins_by_genomic_loc

Reverse genome-to-protein coordinate lookup from the EBI Proteins API: given a genomic position (...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EBIProteins_get_proteins_by_genomic_loc(
    taxonomy: Optional[str | int] = None,
    location: Optional[str] = None,
    chromosome: Optional[str | int] = None,
    position: Optional[str | int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Reverse genome-to-protein coordinate lookup from the EBI Proteins API: given a genomic position (...

    Parameters
    ----------
    taxonomy : str | int
        NCBI taxonomy ID. Default '9606' (human). Example: 9606 (Homo sapiens), 10090...
    location : str
        Genomic location as 'chromosome:position' (1-based). Example: '17:7676154'. P...
    chromosome : str | int
        Chromosome (used with 'position' if 'location' not given). Example: '17', 'X'.
    position : str | int
        1-based genomic position (used with 'chromosome' if 'location' not given). Ex...
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
            "taxonomy": taxonomy,
            "location": location,
            "chromosome": chromosome,
            "position": position,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EBIProteins_get_proteins_by_genomic_loc",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EBIProteins_get_proteins_by_genomic_loc"]
