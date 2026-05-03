"""
UCSC_get_cpg_islands

Get CpG island annotations for a genomic region from UCSC Genome Browser. CpG islands are genomic...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def UCSC_get_cpg_islands(
    chrom: str,
    start: int,
    end: int,
    genome: Optional[str] = "hg38",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get CpG island annotations for a genomic region from UCSC Genome Browser. CpG islands are genomic...

    Parameters
    ----------
    genome : str
        Genome assembly (e.g., 'hg38', 'hg19', 'mm10', 'mm39').
    chrom : str
        Chromosome name (e.g., 'chr17', 'chr1', 'chrX').
    start : int
        Start position (0-based, inclusive).
    end : int
        End position (0-based, exclusive).
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
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "UCSC_get_cpg_islands",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["UCSC_get_cpg_islands"]
