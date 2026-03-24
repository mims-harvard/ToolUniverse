"""
InterVar_classify_variant

Classify a germline variant using ACMG/AMP 2015 standards (InterVar). Returns the clinical signif...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def InterVar_classify_variant(
    chrom: str,
    pos: int,
    ref: str,
    alt: str,
    build: Optional[str] = "hg19",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Classify a germline variant using ACMG/AMP 2015 standards (InterVar). Returns the clinical signif...

    Parameters
    ----------
    chrom : str
        Chromosome number or name. Can include 'chr' prefix (e.g., '17', 'chr17', 'X').
    pos : int
        Genomic position (1-based).
    ref : str
        Reference allele (e.g., 'G', 'A', 'ATCG').
    alt : str
        Alternate allele (e.g., 'A', 'T', 'C').
    build : str
        Genome build. Default: hg19.
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
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
            "build": build,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "InterVar_classify_variant",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["InterVar_classify_variant"]
