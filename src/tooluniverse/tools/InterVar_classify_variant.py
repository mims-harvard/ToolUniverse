"""
InterVar_classify_variant

Classify a germline variant using ACMG/AMP 2015 standards (InterVar). Returns classification
(Pathogenic, Likely Pathogenic, Uncertain Significance, Likely Benign, Benign) and all 28
evidence criteria activation status. No API key required.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def InterVar_classify_variant(
    chrom: str,
    pos: int,
    ref: str,
    alt: str,
    build: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Classify a germline variant using ACMG/AMP 2015 standards (InterVar).

    Parameters
    ----------
    chrom : str
        Chromosome (e.g., '17', 'chr17', 'X').
    pos : int
        Genomic position (1-based).
    ref : str
        Reference allele.
    alt : str
        Alternate allele.
    build : str, optional
        Genome build: 'hg19' or 'hg38'. Default: hg19.
    stream_callback : Callable, optional
        Callback for streaming output.
    use_cache : bool, default False
        Enable caching.
    validate : bool, default True
        Validate parameters.

    Returns
    -------
    dict[str, Any]
    """
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
        {"name": "InterVar_classify_variant", "arguments": _args},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["InterVar_classify_variant"]
