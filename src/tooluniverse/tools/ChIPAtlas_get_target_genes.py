"""
ChIPAtlas_get_target_genes

ChIP-Atlas Target Genes: for a transcription factor, return its ranked list of potential target g...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ChIPAtlas_get_target_genes(
    antigen: str,
    operation: Optional[str] = "get_target_genes",
    genome: Optional[str] = "hg38",
    distance: Optional[str] = "5",
    limit: Optional[int] = 100,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    ChIP-Atlas Target Genes: for a transcription factor, return its ranked list of potential target g...

    Parameters
    ----------
    operation : str

    antigen : str
        Transcription factor / antigen symbol (e.g. 'GATA1', 'CTCF').
    genome : str
        Genome assembly.
    distance : str
        TSS-distance window in kb defining 'bound near a gene'. '1' (±1kb, strict pro...
    limit : int
        Maximum number of top-scoring target genes to return.
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
            "operation": operation,
            "antigen": antigen,
            "genome": genome,
            "distance": distance,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ChIPAtlas_get_target_genes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ChIPAtlas_get_target_genes"]
