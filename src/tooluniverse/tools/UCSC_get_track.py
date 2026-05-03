"""
UCSC_get_track

Get annotation track data from the UCSC Genome Browser for a specified genomic region. Retrieves ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def UCSC_get_track(
    genome: str,
    track: str,
    chrom: str,
    start: int,
    end: int,
    maxItemsOutput: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get annotation track data from the UCSC Genome Browser for a specified genomic region. Retrieves ...

    Parameters
    ----------
    genome : str
        UCSC genome assembly. Examples: 'hg38', 'hg19', 'mm39'.
    track : str
        Track name. Common tracks: 'knownGene' (GENCODE genes), 'ncbiRefSeq' (RefSeq)...
    chrom : str
        Chromosome name. Examples: 'chr1', 'chr17', 'chrX'.
    start : int
        0-based start position (inclusive).
    end : int
        End position (exclusive). Must be > start.
    maxItemsOutput : int | Any
        Maximum number of items to return. Default: 100. Set to limit large result sets.
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
            "track": track,
            "chrom": chrom,
            "start": start,
            "end": end,
            "maxItemsOutput": maxItemsOutput,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "UCSC_get_track",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["UCSC_get_track"]
