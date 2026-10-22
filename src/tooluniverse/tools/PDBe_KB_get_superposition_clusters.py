"""
PDBe_KB_get_superposition_clusters

Get structural superposition clusters for a UniProt protein from PDBe-KB. Segments, clusters with...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PDBe_KB_get_superposition_clusters(
    uniprot_accession: str,
    segment_offset: Optional[int] = 0,
    segment_limit: Optional[int] = 10,
    cluster_offset: Optional[int] = 0,
    cluster_limit: Optional[int] = 10,
    member_offset: Optional[int] = 0,
    member_limit: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get structural superposition clusters for a UniProt protein from PDBe-KB. Segments, clusters with...

    Parameters
    ----------
    uniprot_accession : str
        UniProt accession ID for the protein. Examples: 'P04637' (TP53), 'P00533' (EG...
    segment_offset : int
        Zero-based segment offset.
    segment_limit : int
        Segments to return (default 10, maximum 100).
    cluster_offset : int
        Zero-based cluster offset applied within every returned segment.
    cluster_limit : int
        Clusters returned per segment (default 10, maximum 100).
    member_offset : int
        Zero-based member offset applied within every returned cluster.
    member_limit : int
        Members returned per cluster (default 20, maximum 500).
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
            "uniprot_accession": uniprot_accession,
            "segment_offset": segment_offset,
            "segment_limit": segment_limit,
            "cluster_offset": cluster_offset,
            "cluster_limit": cluster_limit,
            "member_offset": member_offset,
            "member_limit": member_limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PDBe_KB_get_superposition_clusters",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PDBe_KB_get_superposition_clusters"]
