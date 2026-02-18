"""
Dfam_get_annotations

Get transposable element (TE) annotations for a genomic region from Dfam. Returns all TE/repeat e...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Dfam_get_annotations(
    chrom: str,
    start: int,
    end: int,
    assembly: Optional[str] = None,
    nrph: Optional[bool] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get transposable element (TE) annotations for a genomic region from Dfam. Returns all TE/repeat e...

    Parameters
    ----------
    assembly : str
        Genome assembly name (default 'hg38'). Options: 'hg38', 'hg19', 'mm10', 'mm39...
    chrom : str
        Chromosome name (e.g., 'chr1', 'chr17', 'chrX').
    start : int
        Start position (0-based).
    end : int
        End position.
    nrph : bool
        Non-redundant profile hits only (default true). Set false for all hits.
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

    return get_shared_client().run_one_function(
        {
            "name": "Dfam_get_annotations",
            "arguments": {
                "assembly": assembly,
                "chrom": chrom,
                "start": start,
                "end": end,
                "nrph": nrph,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Dfam_get_annotations"]
