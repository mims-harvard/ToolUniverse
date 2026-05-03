"""
CADD_get_variant_score

Get CADD deleteriousness score for a specific variant. PHRED scores: >=20 top 1% deleterious (pat...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CADD_get_variant_score(
    chrom: str,
    pos: int,
    ref: str,
    alt: str,
    version: Optional[str] = "GRCh38-v1.7",
    include_annotations: Optional[bool] = False,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Optional[dict[str, Any]]:
    """
    Get CADD deleteriousness score for a specific variant. PHRED scores: >=20 top 1% deleterious (pat...

    Parameters
    ----------
    chrom : str
        Chromosome (1-22, X, Y, MT). Can include 'chr' prefix.
    pos : int
        Genomic position (1-based)
    ref : str
        Reference allele (e.g., 'A', 'G')
    alt : str
        Alternate allele (e.g., 'T', 'C')
    version : str
        CADD version and genome build
    include_annotations : bool
        Include full annotation details in response
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    Optional[dict[str, Any]]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "chrom": chrom,
            "pos": pos,
            "ref": ref,
            "alt": alt,
            "version": version,
            "include_annotations": include_annotations,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "CADD_get_variant_score",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CADD_get_variant_score"]
