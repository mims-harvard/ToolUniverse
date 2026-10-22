"""
EBIProteins_get_coordinate_mapping

Map UniProt protein positions to genomic coordinates at exon-level resolution. Transcript coordin...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EBIProteins_get_coordinate_mapping(
    accession: str,
    coordinate_offset: Optional[int] = 0,
    coordinate_limit: Optional[int] = 10,
    exon_offset: Optional[int] = 0,
    exon_limit: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Map UniProt protein positions to genomic coordinates at exon-level resolution. Transcript coordin...

    Parameters
    ----------
    accession : str
        UniProt accession. Examples: 'P04637' (TP53), 'P00533' (EGFR), 'P38398' (BRCA...
    coordinate_offset : int
        Zero-based transcript coordinate-mapping offset.
    coordinate_limit : int
        Coordinate mappings returned per page (default 10, maximum 500).
    exon_offset : int
        Zero-based exon offset applied within every returned coordinate mapping.
    exon_limit : int
        Exons returned per coordinate mapping (default 20, maximum 1000).
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
            "accession": accession,
            "coordinate_offset": coordinate_offset,
            "coordinate_limit": coordinate_limit,
            "exon_offset": exon_offset,
            "exon_limit": exon_limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EBIProteins_get_coordinate_mapping",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EBIProteins_get_coordinate_mapping"]
