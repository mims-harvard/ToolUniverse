"""
UCSC_get_tf_binding_clusters

Get Transcription Factor ChIP-seq Clusters from ENCODE3 for a genomic region via UCSC Genome Brow...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def UCSC_get_tf_binding_clusters(
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
    Get Transcription Factor ChIP-seq Clusters from ENCODE3 for a genomic region via UCSC Genome Brow...

    Parameters
    ----------
    genome : str
        Genome assembly (e.g., 'hg38', 'hg19').
    chrom : str
        Chromosome name (e.g., 'chr17').
    start : int
        Start position (0-based).
    end : int
        End position (0-based).
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
            "name": "UCSC_get_tf_binding_clusters",
            "arguments": {"genome": genome, "chrom": chrom, "start": start, "end": end},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["UCSC_get_tf_binding_clusters"]
