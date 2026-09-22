"""
UCSC_get_sequence

Get DNA sequence from the UCSC Genome Browser for a genomic region. Pass 'region' as a written lo...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def UCSC_get_sequence(
    genome: str,
    chrom: Optional[str] = None,
    start: Optional[int] = None,
    end: Optional[int] = None,
    region: Optional[str] = None,
    coordinate_system: Optional[str] = "0-based",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get DNA sequence from the UCSC Genome Browser for a genomic region. Pass 'region' as a written lo...

    Parameters
    ----------
    genome : str
        UCSC genome assembly identifier. Examples: 'hg38' (human), 'mm39' (mouse), 'd...
    chrom : str
        Chromosome name. Examples: 'chr1', 'chr17', 'chrX', 'chrM'.
    start : int
        Start position. Interpreted per 'coordinate_system' (default 0-based, inclusi...
    end : int
        End position. Exclusive when coordinate_system is 0-based, inclusive when 1-b...
    region : str
        Genomic region written the usual way, 1-based INCLUSIVE on both ends, e.g. 'c...
    coordinate_system : str
        Which convention chrom/start/end are given in. '0-based' (default) is half-op...
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
            "genome": genome,
            "chrom": chrom,
            "start": start,
            "end": end,
            "region": region,
            "coordinate_system": coordinate_system,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "UCSC_get_sequence",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["UCSC_get_sequence"]
