"""
Ensembl_get_transcript_haplotypes

Get population protein and CDS haplotypes for a transcript from the Ensembl REST API (transcript_...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Ensembl_get_transcript_haplotypes(
    id: str,
    species: Optional[str] = "human",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get population protein and CDS haplotypes for a transcript from the Ensembl REST API (transcript_...

    Parameters
    ----------
    id : str
        Ensembl transcript stable ID. Examples: 'ENST00000288602' (BRAF), 'ENST000002...
    species : str
        Species name (default 'human'). Use 'human' or 'homo_sapiens'.
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
    _args = {k: v for k, v in {"id": id, "species": species}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "Ensembl_get_transcript_haplotypes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Ensembl_get_transcript_haplotypes"]
